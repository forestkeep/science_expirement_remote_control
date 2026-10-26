"""AnalysisController — центральный Mediator подсистемы анализа."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication

from graphs.core.session_mode import SessionMode

from .commands import (
    ApplyAnalysisCommand, ApplyUncertaintyCommand, RemoveAnalysisCommand,
    RemoveUncertaintyCommand, UpdateAnalysisParamsCommand
)
from .models import (
    AnalysisArtifact, SourceSnapshot,
)
from .preview import AnalysisPreviewManager
from .registry import AnalysisToolRegistry
from .renderers.adapter import AnalysisRendererAdapter
from .store import SessionAnalysisStore
from .uncertainty import UncertaintyRecord, compute_uncertainty

logger = logging.getLogger(__name__)
_TR = lambda s: QApplication.translate("GraphWindow", s)


@dataclass
class ToolSession:
    tool_id: str
    params: Dict[str, Any]
    sources: List[SourceSnapshot]
    leader_index: int
    preview_handle: Any = None


class AnalysisController(QObject):
    tool_activated = pyqtSignal(str)
    tool_deactivated = pyqtSignal()
    preview_updated = pyqtSignal()
    artifact_applied = pyqtSignal(str)
    artifact_removed = pyqtSignal(str)
    artifacts_changed = pyqtSignal()

    def __init__(self, session, parent=None) -> None:
        super().__init__(parent)
        self.session = session
        self.store = SessionAnalysisStore()
        self.preview = AnalysisPreviewManager()
        self.renderer = AnalysisRendererAdapter(session)
        self.registry = AnalysisToolRegistry.instance()
        self._active: Optional[ToolSession] = None
        self._uncertainty_archive: Dict[str, UncertaintyRecord] = {}
        self._highlighted: set = set()

        # Связь с выделением кривых
        model = getattr(session, "selection_model", None)
        if model is not None:
            model.selection_changed.connect(self._on_selection_changed)

    # ------------------------------------------------------------------
    # Публичный API
    # ------------------------------------------------------------------
    def activate_tool(self, tool_id: str, sources: Optional[List[str]] = None) -> bool:
        if self.session.mode == SessionMode.LIVE:
            return False
        desc = self.registry.get(tool_id)
        if desc is None:
            return False

        snapshots = self._collect_sources(sources)
        if not snapshots:
            return False

        # Если уже активен другой инструмент — сбросить
        if self._active is not None and self._active.tool_id != tool_id:
            self._active = None

        leader_index = len(snapshots) - 1  # лидер = последняя выделенная
        params = {p.name: p.default for p in desc.param_schema}
        self._active = ToolSession(tool_id=tool_id, params=params,
                                   sources=snapshots, leader_index=leader_index)
        self.tool_activated.emit(tool_id)
        return True

    def cancel_preview(self) -> None:
        """Полный сброс активного инструмента (без создания артефакта)."""
        if self._active is not None:
            if self._active.preview_handle is not None:
                self.renderer.remove(self._active.preview_handle)
        self.preview.clear()
        self._active = None
        self.preview_updated.emit()
        self.tool_deactivated.emit()

    def set_preview_params(self, params: Dict[str, Any]) -> None:
        """Обновить параметры активного инструмента (без предпросмотра)."""
        if self._active is None:
            return
        self._active.params.update(params)

    def apply(self) -> List[str]:
        """Применить активный инструмент. Идемпотентно: сначала удаляются
        прежние артефакты этого же инструмента для тех же источников."""
        if self._active is None:
            return []
        tool_id = self._active.tool_id
        desc = self.registry.get(tool_id)
        if desc is None:
            return []
        created: List[str] = []

        # --- снести предыдущие артефакты этого инструмента по тем же кривым ---
        source_ids = {s.root_name for s in self._active.sources}
        for art in list(self.store.all()):
            if art.tool_id == tool_id and set(art.source_curve_ids) & source_ids:
                self._do_remove(art.id)

        if tool_id == "uncertainty.estimate":
            # Погрешности хранятся прямо в CurveDataStore. При повторном
            # применении (после смены параметров) сначала сносим старые
            # записи для тех же кривых — иначе они наслаиваются друг на друга
            # и смена метода/окна визуально не видна.
            for snap in self._active.sources:
                curve = self.session.graph_main.get_curve(snap.root_name)
                if curve is None:
                    continue
                store = getattr(curve, "store", None)
                if store is None:
                    continue
                for rec in list(getattr(store, "uncertainty_records", []) or []):
                    self._do_remove_uncertainty(snap.root_name, rec.id)
            # Добавить новые записи
            for snap in self._active.sources:
                record = self._compute_uncertainty_record(snap, self._active.params)
                cmd = ApplyUncertaintyCommand(self, snap.root_name, record)
                self.session.undo_manager.push(cmd, execute=True)
            self.artifacts_changed.emit()
            return created

        strategy = self.registry.create_strategy(tool_id)
        if strategy is None:
            return []

        from .strategies.base import AnalysisContext
        ctx = AnalysisContext(
            sources=self._active.sources,
            filter_instance=getattr(self.session, "filter_class", None),
            alias_manager=getattr(self.session, "alias_manager", None),
        )
        try:
            payload, details = strategy.compute(ctx, self._active.params)
        except Exception:
            logger.exception("apply: compute failed")
            return []

        for i, snap in enumerate(self._active.sources):
            sub_payload = self._payload_for_source(payload, i)
            artifact = AnalysisArtifact(
                tool_id=tool_id,
                source_curve_ids=[snap.root_name],
                params=dict(self._active.params),
                placement_type=desc.placement_type,
                payload=sub_payload,
                description=strategy.describe(self._active.params),
                leader_curve_id=snap.root_name,
            )
            cmd = ApplyAnalysisCommand(self, artifact)
            self.session.undo_manager.push(cmd, execute=True)
            created.append(artifact.id)

        self.artifacts_changed.emit()
        return created

    def apply_uncertainty_live(self) -> None:
        """Пересчитать погрешности активного инструмента без undo-команд.

        Используется, когда пользователь меняет параметры «Погрешностей
        точек» на лету: записи в ``CurveDataStore`` обновляются сразу,
        но история undo не засоряется промежуточными состояниями.
        Undo фиксируется только при явном «Применить» (см. ``apply``).
        """
        if self._active is None or self._active.tool_id != "uncertainty.estimate":
            return
        for snap in self._active.sources:
            curve = self.session.graph_main.get_curve(snap.root_name)
            if curve is None:
                continue
            store = getattr(curve, "store", None)
            if store is None:
                continue
            for rec in list(getattr(store, "uncertainty_records", []) or []):
                self._do_remove_uncertainty(snap.root_name, rec.id)
            record = self._compute_uncertainty_record(snap, self._active.params)
            self._do_apply_uncertainty(snap.root_name, record)
        self.artifacts_changed.emit()

    def remove_uncertainty(self, root_name: str, record_id: str) -> None:
        """Удалить запись погрешности (undoable)."""
        cmd = RemoveUncertaintyCommand(self, root_name, record_id)
        self.session.undo_manager.push(cmd, execute=True)
        self.artifacts_changed.emit()

    def on_source_name_changed(self, root_name: str) -> None:
        """Кривая переименована — обновить подписи её артефактов в легендах.

        Данные и handle'ы не трогаем — только текст в LegendItem.
        """
        for art in self._artifacts_for_source(root_name):
            try:
                self.renderer.update_legend_names(art)
            except Exception:
                logger.exception(
                    "on_source_name_changed: %s failed", art.id
                )

    def on_source_style_changed(self, root_name: str) -> None:
        """Кривая изменила стиль — перерисовать её артефакты (производная,
        интеграл, FFT, фитинги, …) и error-bars, чтобы они подхватили
        новый цвет/толщину/маркер.
        """
        # 1. Артефакты анализа
        for art in list(self.store.for_curve(root_name)):
            try:
                old_handle = art.handle
                if old_handle is not None:
                    self.renderer.remove(old_handle)
                new_handle = self.renderer.render(art, is_preview=False)
                art.handle = new_handle
                if new_handle is not None:
                    self.renderer.set_visible(new_handle, art.visibility)
            except Exception:
                logger.exception(
                    "on_source_style_changed: re-render %s failed", art.id
                )

        # 2. Полосы погрешностей на самой кривой (uncertainty)
        curve = self.session.graph_main.get_curve(root_name)
        if curve is not None:
            store = getattr(curve, "store", None)
            if store is not None and hasattr(curve.presenter, "set_error_bars"):
                try:
                    curve.presenter.set_error_bars(store.active_uncertainty_records())
                except Exception:
                    logger.exception(
                        "on_source_style_changed: error bars failed"
                    )

        self.artifacts_changed.emit()

    def apply_preset(self, preset, sources: Optional[List[str]] = None) -> int:
        if preset is None or not getattr(preset, "artifacts", None):
            return 0

        snapshots = self._collect_sources(sources)
        if not snapshots:
            return 0

        applied = 0
        for entry in preset.artifacts:
            tool_id = entry.get("tool_id")
            if not tool_id or self.registry.get(tool_id) is None:
                continue
            params = dict(entry.get("params") or {})

            self._active = ToolSession(
                tool_id=tool_id,
                params=params,
                sources=list(snapshots),
                leader_index=len(snapshots) - 1,
            )
            try:
                created = self.apply()
                if created or tool_id == "uncertainty.estimate":
                    applied += 1
            except Exception:
                logger.exception("apply_preset: tool %s failed", tool_id)
            finally:
                self._active = None

        self.artifacts_changed.emit()
        return applied

    def set_uncertainty_visible(self, root_name: str, record_id: str,
                                 visible: bool) -> None:
        """Включить/выключить показ конкретной записи погрешности."""
        curve = self.session.graph_main.get_curve(root_name)
        if curve is None:
            return
        store = getattr(curve, "store", None)
        if store is None:
            return
        store.set_uncertainty_active(record_id, visible)
        if hasattr(curve.presenter, "set_error_bars"):
            curve.presenter.set_error_bars(store.active_uncertainty_records())
        self.artifacts_changed.emit()

    def set_uncertainty_style(self, root_name: str, style: Dict[str, Any]) -> None:
        """Обновить стиль отображения погрешностей для всех записей кривой.

        Стиль также запоминается в ``store.uncertainty_style`` — он будет
        применён к новым записям, создаваемым через ``apply()``.
        """
        curve = self.session.graph_main.get_curve(root_name)
        if curve is None:
            return
        store = getattr(curve, "store", None)
        if store is None:
            return
        from .uncertainty import normalize_uncertainty_style
        new_style = normalize_uncertainty_style(style or {})
        store.uncertainty_style = dict(new_style)
        for rec in getattr(store, "uncertainty_records", []) or []:
            rec.style = dict(new_style)
        if hasattr(curve.presenter, "set_error_bars"):
            curve.presenter.set_error_bars(store.active_uncertainty_records())
        self.artifacts_changed.emit()

    def get_uncertainty_style(self, root_name: str) -> Optional[Dict[str, Any]]:
        """Прочитать текущий стиль погрешностей (шаблон + значение по умолчанию)."""
        curve = self.session.graph_main.get_curve(root_name)
        if curve is None:
            return None
        store = getattr(curve, "store", None)
        if store is None:
            return None
        from .uncertainty import normalize_uncertainty_style
        style = dict(getattr(store, "uncertainty_style", {}) or {})
        if not style and getattr(store, "uncertainty_records", None):
            style = dict(store.uncertainty_records[0].style or {})
        return normalize_uncertainty_style(style)

    def _on_selection_changed(self, selected) -> None:
        """Подсветить артефакты, чьи источники выделены."""
        selected_roots = set()
        for item in selected or []:
            root = None
            if hasattr(item, "store") and hasattr(item.store, "rel_data"):
                root = item.store.rel_data.root_name
            elif hasattr(item, "rel_data"):
                root = item.rel_data.root_name
            if root:
                selected_roots.add(root)

        for art in self.store.all():
            is_sel = any(s in selected_roots for s in art.source_curve_ids)
            if is_sel and art.id not in self._highlighted:
                self._highlighted.add(art.id)
                try:
                    self.renderer.set_highlighted(art.handle, True)
                except Exception:
                    pass
            elif not is_sel and art.id in self._highlighted:
                self._highlighted.discard(art.id)
                try:
                    self.renderer.set_highlighted(art.handle, False)
                except Exception:
                    pass

    def remove_artifact(self, artifact_id: str) -> None:
        artifact = self.store.get(artifact_id)
        if artifact is None:
            return
        cmd = RemoveAnalysisCommand(self, artifact)
        self.session.undo_manager.push(cmd, execute=True)
        self.artifacts_changed.emit()

    def update_artifact_params(self, artifact_id: str, params: Dict[str, Any]) -> None:
        artifact = self.store.get(artifact_id)
        if artifact is None:
            return
        old_params = dict(artifact.params)
        old_payload = artifact.payload
        # пересчёт
        desc = self.registry.get(artifact.tool_id)
        strategy = self.registry.create_strategy(artifact.tool_id)
        if strategy is None:
            return
        snapshots = self._collect_sources(artifact.source_curve_ids)
        from .strategies.base import AnalysisContext
        ctx = AnalysisContext(sources=snapshots,
                              filter_instance=getattr(self.session, "filter_class", None))
        payload, _ = strategy.compute(ctx, params)
        new_payload = self._payload_for_source(payload, 0)
        cmd = UpdateAnalysisParamsCommand(self, artifact_id, old_params, params,
                                          old_payload, new_payload)
        self.session.undo_manager.push(cmd, execute=True)
        self.artifacts_changed.emit()

    # ------------------------------------------------------------------
    # Внутренний помощник: артефакты, привязанные к источнику
    # ------------------------------------------------------------------
    def _artifacts_for_source(self, root_name: str) -> List[AnalysisArtifact]:
        return [art for art in self.store.all() if root_name in art.source_curve_ids]

    def on_source_hidden(self, root_name: str) -> None:
        """Источник скрыт — все его артефакты физически удаляются из легенды
        и скрываются на графике, независимо от их чекбоксов."""
        for art in self._artifacts_for_source(root_name):
            try:
                self.renderer.set_visible(art.handle, False)
            except Exception:
                logger.exception("on_source_hidden: set_visible failed")
        self.artifacts_changed.emit()

    def on_source_shown(self, root_name: str) -> None:
        """Источник показан — видимость артефактов возвращается к их чекбоксам."""
        for art in self._artifacts_for_source(root_name):
            try:
                self.renderer.set_visible(art.handle, bool(art.visibility))
            except Exception:
                logger.exception("on_source_shown: set_visible failed")
        self.artifacts_changed.emit()

    def set_artifact_visibility(self, artifact_id: str, visible: bool) -> None:
        """Переключение видимости артефакта через его чекбокс.

        Чекбокс — единственный источник правды для artifact.visibility;
        при включении чекбокса артефакт возвращается и в легенду, и на график.
        """
        artifact = self.store.get(artifact_id)
        if artifact is None:
            return
        artifact.visibility = bool(visible)
        self.renderer.set_visible(artifact.handle, bool(visible))
        self.artifacts_changed.emit()

    def get_artifacts_for_curve(self, root_name: str) -> List[AnalysisArtifact]:
        return self.store.for_curve(root_name)

    def get_active_tool(self) -> Optional[ToolSession]:
        return self._active

    # ------------------------------------------------------------------
    # Внутренние операции (вызываются undo-командами)
    # ------------------------------------------------------------------
    def _do_apply(self, artifact: AnalysisArtifact) -> None:
        self.store.add(artifact)
        handle = self.renderer.render(artifact, is_preview=False)
        artifact.handle = handle
        self.renderer.set_visible(handle, artifact.visibility)
        self.artifact_applied.emit(artifact.id)

    def _do_remove(self, artifact_id: str) -> None:
        artifact = self.store.get(artifact_id)
        if artifact is None:
            return
        self.renderer.remove(artifact.handle)
        self.store.remove(artifact_id)
        self.artifact_removed.emit(artifact_id)

    def _do_update_params(self, artifact_id: str, params: Dict[str, Any], payload) -> None:
        artifact = self.store.get(artifact_id)
        if artifact is None:
            return
        artifact.params = dict(params)
        artifact.payload = payload
        self.renderer.update(artifact.handle, payload)

    def _do_apply_uncertainty(self, root_name: str, record: UncertaintyRecord) -> None:
        curve = self.session.graph_main.get_curve(root_name)
        if curve is None:
            return
        store = curve.store
        store.uncertainty_records.append(record)
        store.active_uncertainty_ids.add(record.id)
        self._uncertainty_archive[record.id] = record
        if hasattr(curve.presenter, "set_error_bars"):
            curve.presenter.set_error_bars(store.active_uncertainty_records())
        store._notify_changed()

    def _do_remove_uncertainty(self, root_name: str, record_id: str) -> None:
        curve = self.session.graph_main.get_curve(root_name)
        if curve is None:
            return
        store = curve.store
        store.uncertainty_records = [r for r in store.uncertainty_records if r.id != record_id]
        store.active_uncertainty_ids.discard(record_id)
        if hasattr(curve.presenter, "set_error_bars"):
            curve.presenter.set_error_bars(store.active_uncertainty_records())
        store._notify_changed()

    def _do_restore_uncertainty(self, root_name: str, record_id: str) -> None:
        record = self._uncertainty_archive.get(record_id)
        if record is None:
            return
        self._do_apply_uncertainty(root_name, record)

    # ------------------------------------------------------------------
    # Внутренние помощники
    # ------------------------------------------------------------------
    def _collect_sources(self, sources: Optional[List[str]]) -> List[SourceSnapshot]:
        selected_ids = sources
        if selected_ids is None:
            selected_ids = self._selected_curve_ids()
        result: List[SourceSnapshot] = []
        for root_name in selected_ids:
            curve = self.session.graph_main.get_curve(root_name)
            if curve is None:
                continue
            result.append(SourceSnapshot(
                root_name=root_name,
                x=curve.filtered_x_data,
                y=curve.filtered_y_data,
                x_name=curve.rel_data.x_current_name,
                y_name=curve.rel_data.y_current_name,
                device=getattr(curve, "device", "") or "",
                ch=getattr(curve, "ch", "") or "",
                number_axis=curve.number_axis or 1,
                saved_style=curve.saved_style,
                curve_name=curve.curve_name,
            ))
        return result

    def _selected_curve_ids(self) -> List[str]:
        model = getattr(self.session, "selection_model", None)
        if model is None:
            return []
        ids: List[str] = []
        for item in model.current():
            root_name = None
            if hasattr(item, "store") and hasattr(item.store, "rel_data"):
                root_name = item.store.rel_data.root_name
            elif hasattr(item, "rel_data"):
                root_name = item.rel_data.root_name
            if root_name and root_name not in ids:
                ids.append(root_name)
        return ids

    def _compute_uncertainty_record(self, snap: SourceSnapshot,
                                     params: Dict[str, Any]) -> UncertaintyRecord:
        method = params.get("method", "std")
        rec = compute_uncertainty(method, snap.x, snap.y, params)
        # Перенести сохранённый стиль кривой на новую запись
        curve = self.session.graph_main.get_curve(snap.root_name)
        if curve is not None:
            store_style = getattr(curve.store, "uncertainty_style", None) or {}
            if store_style:
                from .uncertainty import normalize_uncertainty_style
                rec.style = normalize_uncertainty_style(store_style)
        return rec

    def _payload_for_source(self, payload, index: int):
        """Возвращает payload, содержащий только данные для одного источника."""
        kind = getattr(payload, "kind", None)
        if kind == "overlay":
            xs = getattr(payload, "x", [])
            ys = getattr(payload, "y", [])
            return type(payload)(
                x=[xs[index]] if index < len(xs) else [],
                y=[ys[index]] if index < len(ys) else [],
                style_hint=getattr(payload, "style_hint", {}),
            )
        if kind == "attached":
            xs = getattr(payload, "x", [])
            ys = getattr(payload, "y", [])
            return type(payload)(
                x=[xs[index]] if index < len(xs) else [],
                y=[ys[index]] if index < len(ys) else [],
                y_label=payload.y_label,
                panel_title=payload.panel_title,
            )
        if kind == "domain":
            xs = getattr(payload, "x", [])
            ys = getattr(payload, "y", [])
            return type(payload)(
                x=[xs[index]] if index < len(xs) else [],
                y=[ys[index]] if index < len(ys) else [],
                x_label=payload.x_label,
                y_label=payload.y_label,
                tab_title=payload.tab_title,
            )
        if kind == "annotation":
            pts = [p for p in getattr(payload, "points", [])]
            return type(payload)(points=pts, label=payload.label)
        return payload