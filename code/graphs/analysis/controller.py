"""AnalysisController — центральный Mediator подсистемы анализа."""
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from PyQt5.QtCore import QObject, QTimer, pyqtSignal
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

        # --- Авто-пересчёт артефактов и погрешностей при изменении filtered_* ---
        self._subscribed_curves: Dict[str, Any] = {}
        self._pending_recompute: Set[str] = set()
        # Версия данных кривой на момент последнего пересчёта. Используется,
        # чтобы не запускать пересчёт на холостых data_changed (например,
        # от изменения uncertainty_records: это метаданные, не данные).
        self._last_data_version: Dict[str, int] = {}
        self._recomputing: bool = False
        self._recompute_timer = QTimer(self)
        self._recompute_timer.setSingleShot(True)
        self._recompute_timer.setInterval(150)
        self._recompute_timer.timeout.connect(self._flush_recompute)

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

    # ------------------------------------------------------------------
    # Публичный API: apply
    # ------------------------------------------------------------------
    def apply(self) -> List[str]:
        if self._active is None:
            return []
        tool_id = self._active.tool_id
        descriptor = self.registry.get(tool_id)
        if descriptor is None:
            return []

        # КЛЮЧЕВОЕ: снапшоты, взятые в activate_tool(), могли устареть —
        # пользователь мог применить/снять/изменить фильтры, отредактировать
        # точки или дождаться нового батча в live-сессии. Пересобираем их
        # из АКТУАЛЬНЫХ filtered_* данных: поиск пиков, фитинги, FFT и т.д.
        # должны видеть ту же кривую, которую видит пользователь.
        source_root_names = [s.root_name for s in self._active.sources]
        fresh_sources = self._collect_sources(source_root_names)
        if not fresh_sources:
            return []
        self._active.sources = fresh_sources

        created: List[str] = []

        # --- снести предыдущие артефакты этого инструмента по тем же кривым ---
        source_ids = {s.root_name for s in self._active.sources}
        for art in list(self.store.all()):
            if art.tool_id == tool_id and set(art.source_curve_ids) & source_ids:
                self._do_remove(art.id)

        if tool_id == "uncertainty.estimate":
            for snap in self._active.sources:
                curve = self.session.graph_main.get_curve(snap.root_name)
                if curve is None:
                    continue
                store = getattr(curve, "store", None)
                if store is None:
                    continue
                for rec in list(getattr(store, "uncertainty_records", []) or []):
                    self._do_remove_uncertainty(snap.root_name, rec.id)
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
            sub_payload = self._payload_for_source(payload, i, snap.root_name)
            description = self._build_artifact_description(
                strategy, self._active.params, sub_payload, details,
                snap.root_name,
            )
            artifact = AnalysisArtifact(
                tool_id=tool_id,
                source_curve_ids=[snap.root_name],
                params=dict(self._active.params),
                placement_type=descriptor.placement_type,
                payload=sub_payload,
                description=description,
                leader_curve_id=snap.root_name,
            )
            cmd = ApplyAnalysisCommand(self, artifact)
            self.session.undo_manager.push(cmd, execute=True)
            created.append(artifact.id)

        self.artifacts_changed.emit()
        return created

    def apply_uncertainty_live(self) -> None:
        """Пересчитать погрешности активного инструмента без undo-команд."""
        if self._active is None or self._active.tool_id != "uncertainty.estimate":
            return

        # Снапшот мог устареть между активацией и живым редактированием
        # (например, пользователь менял фильтр до того, как открыл
        # параметры погрешности). Пересобираем — запись должна считаться
        # по текущей кривой.
        source_root_names = [s.root_name for s in self._active.sources]
        fresh_sources = self._collect_sources(source_root_names)
        if fresh_sources:
            self._active.sources = fresh_sources

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

    # ------------------------------------------------------------------
    def update_artifact_params(self, artifact_id: str,
                               params: Dict[str, Any]) -> None:
        artifact = self.store.get(artifact_id)
        if artifact is None:
            return
        old_params = dict(artifact.params)
        old_payload = artifact.payload
        old_description = artifact.description

        strategy = self.registry.create_strategy(artifact.tool_id)
        if strategy is None:
            return

        snapshots = self._collect_sources(artifact.source_curve_ids)
        if not snapshots:
            return

        from .strategies.base import AnalysisContext
        ctx = AnalysisContext(
            sources=snapshots,
            filter_instance=getattr(self.session, "filter_class", None),
        )
        try:
            payload, details = strategy.compute(ctx, params)
        except Exception:
            logger.exception("update_artifact_params: compute failed")
            return

        source_id = (artifact.source_curve_ids[0]
                     if artifact.source_curve_ids else None)
        new_payload = self._payload_for_source(payload, 0, source_id)
        new_description = self._build_artifact_description(
            strategy, params, new_payload, details, source_id,
        )

        cmd = UpdateAnalysisParamsCommand(
            self, artifact_id, old_params, params,
            old_payload, new_payload,
            old_description, new_description,
        )
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
        for root_name in artifact.source_curve_ids:
            self._subscribe_curve(root_name)
        self.artifact_applied.emit(artifact.id)

    def _do_remove(self, artifact_id: str) -> None:
        artifact = self.store.get(artifact_id)
        if artifact is None:
            return
        self.renderer.remove(artifact.handle)
        self.store.remove(artifact_id)
        for root_name in artifact.source_curve_ids:
            self._maybe_unsubscribe_curve(root_name)
        self.artifact_removed.emit(artifact_id)


    # ------------------------------------------------------------------
    # Описание артефакта — единая точка правды
    # ------------------------------------------------------------------
    def _build_artifact_description(self, strategy, params: Dict[str, Any],
                                    sub_payload, details,
                                    root_name: Optional[str]) -> str:
        """Собрать описание с расшифровкой «показано N из M».

        Для аннотаций (пики, впадины) дополняем describe() контекстом:
        сколько всего найдено и показано. Для прочих типов — просто
        strategy.describe(params).
        """
        base = strategy.describe(params)
        if getattr(sub_payload, "kind", None) != "annotation":
            return base

        n = len(getattr(sub_payload, "points", []) or [])
        total = n
        for d in (details or []):
            if root_name is not None and d.get("curve") == root_name:
                total = d.get("total_found", n)
                break

        if total > n:
            tail = f"показано {n} из {total} — увеличьте max_points или min_prominence"
        elif n == 0:
            tail = "ничего не найдено — ослабьте фильтры"
        else:
            tail = f"найдено: {n}"
        return f"{base}; {tail}" if base else tail

    # ------------------------------------------------------------------
    # Подписка/отписка на изменения данных кривой
    # ------------------------------------------------------------------
    def _subscribe_curve(self, root_name: str) -> None:
        if root_name in self._subscribed_curves:
            return
        curve = self.session.graph_main.get_curve(root_name)
        if curve is None:
            return
        store = getattr(curve, "store", None)
        if store is None:
            return
        callback = lambda rn=root_name: self._on_source_data_changed(rn)
        store.on_data_changed(callback)
        self._subscribed_curves[root_name] = callback

    def _unsubscribe_curve(self, root_name: str) -> None:
        callback = self._subscribed_curves.pop(root_name, None)
        if callback is None:
            return
        curve = self.session.graph_main.get_curve(root_name)
        if curve is None:
            return
        store = getattr(curve, "store", None)
        if store is not None:
            store.off_data_changed(callback)

    # ------------------------------------------------------------------
    # Дебаунсенный пересчёт
    # ------------------------------------------------------------------
    def _on_source_data_changed(self, root_name: str) -> None:
        """Данные кривой изменились. Артефакты анализа и записи погрешности
        на этой кривой устарели и должны быть пересчитаны по новым
        filtered_*.

        Защита от холостых вызовов: ``_notify_changed()`` эмитится не только
        при изменении filtered-данных, но и при операциях над записями
        погрешности (добавление/удаление). Отслеживаем ``data_version``:
        бампается только на реальных изменениях данных, поэтому на
        uncertainty-операциях version не сдвигается и пересчёт не
        запускается.
        """
        curve = self.session.graph_main.get_curve(root_name)
        if curve is None:
            return
        store = getattr(curve, "store", None)
        if store is None:
            return

        current_version = getattr(store, "data_version", 0)
        if current_version == self._last_data_version.get(root_name, -1):
            return

        has_artifacts = bool(self.store.for_curve(root_name))
        has_uncertainty = bool(getattr(store, "uncertainty_records", None))
        if not (has_artifacts or has_uncertainty):
            return

        self._last_data_version[root_name] = current_version
        self._pending_recompute.add(root_name)
        self._recompute_timer.start()

    def _flush_recompute(self) -> None:
        if not self._pending_recompute:
            return
        pending = list(self._pending_recompute)
        self._pending_recompute.clear()

        if self._recomputing:
            self._pending_recompute.update(pending)
            self._recompute_timer.start()
            return

        self._recomputing = True
        try:
            for root_name in pending:
                # Погрешности — дешевле (нет remove+render), идут первыми.
                self._recompute_uncertainty_for(root_name)
                for artifact in list(self.store.for_curve(root_name)):
                    self._recompute_artifact(artifact)
        finally:
            self._recomputing = False
        self.artifacts_changed.emit()

    def _recompute_uncertainty_for(self, root_name: str) -> None:
        """Пересчитать y_err всех записей погрешности кривой.

        Сохраняем identity каждой записи (``id``, ``style``, ``created_at``,
        ``visibility``) — пересчитываем только геометрию полос. Undo-команду
        не создаём: пересчёт — следствие изменения фильтра, отмена фильтра
        автоматически вернёт погрешности к прежнему виду.
        """
        curve = self.session.graph_main.get_curve(root_name)
        if curve is None:
            return
        store = getattr(curve, "store", None)
        if store is None:
            return

        records = list(getattr(store, "uncertainty_records", []) or [])
        if not records:
            return

        x = store.filtered_x_data
        y = store.filtered_y_data
        if len(x) == 0 or len(y) == 0:
            return

        for rec in records:
            try:
                fresh = compute_uncertainty(
                    getattr(rec, "method", "std"),
                    x, y,
                    dict(getattr(rec, "params", {}) or {}),
                )
            except Exception:
                logger.exception(
                    "_recompute_uncertainty_for: compute failed for %s", rec.id
                )
                continue
            # Копируем только геометрию; style/id/created_at остаются
            # на исходной записи.
            rec.y_err = fresh.y_err
            rec.x_err = fresh.x_err

        if hasattr(curve.presenter, "set_error_bars"):
            try:
                curve.presenter.set_error_bars(
                    store.active_uncertainty_records()
                )
            except Exception:
                logger.exception(
                    "_recompute_uncertainty_for: set_error_bars failed"
                )

    def _maybe_unsubscribe_curve(self, root_name: str) -> None:
        """Отписаться от изменений данных кривой, если на ней больше нет
        ни артефактов анализа, ни записей погрешности.
        """
        if self.store.for_curve(root_name):
            return
        curve = self.session.graph_main.get_curve(root_name)
        if curve is None:
            return
        store = getattr(curve, "store", None)
        if store is None:
            return
        if getattr(store, "uncertainty_records", None):
            return
        self._unsubscribe_curve(root_name)

    def _recompute_artifact(self, artifact: AnalysisArtifact) -> None:
        """Пересчитать артефакт на актуальных filtered_* данных.

        Undo-команду НЕ создаём: пересчёт — следствие изменения фильтров,
        а не самостоятельное действие пользователя. Undo фильтра сам
        вернёт артефакт к прежнему состоянию через обычный recompute.
        """
        strategy = self.registry.create_strategy(artifact.tool_id)
        if strategy is None:
            return

        snapshots = self._collect_sources(artifact.source_curve_ids)
        if not snapshots:
            return

        from .strategies.base import AnalysisContext
        ctx = AnalysisContext(
            sources=snapshots,
            filter_instance=getattr(self.session, "filter_class", None),
        )
        params = dict(artifact.params)
        try:
            payload, details = strategy.compute(ctx, params)
        except Exception:
            logger.exception(
                "_recompute_artifact: compute failed for %s", artifact.id
            )
            return

        source_id = (artifact.source_curve_ids[0]
                     if artifact.source_curve_ids else None)
        new_payload = self._payload_for_source(payload, 0, source_id)
        new_description = self._build_artifact_description(
            strategy, params, new_payload, details, source_id,
        )
        self._do_update_params(artifact.id, params, new_payload, new_description)

    # ------------------------------------------------------------------
    def _do_update_params(self, artifact_id: str, params: Dict[str, Any],
                          payload, description: Optional[str] = None) -> None:
        artifact = self.store.get(artifact_id)
        if artifact is None:
            return

        kind = getattr(payload, "kind", None)
        if kind == "annotation":
            # Аннотации требуют полного перерендера — точки другие.
            self.renderer.remove(artifact.handle)
            artifact.handle = None

            artifact.params = dict(params)
            artifact.payload = payload
            if description is not None:
                artifact.description = description

            handle = self.renderer.render(artifact, is_preview=False)
            artifact.handle = handle
            self.renderer.set_visible(handle, artifact.visibility)
            return

        artifact.params = dict(params)
        artifact.payload = payload
        if description is not None:
            artifact.description = description
        self.renderer.update(artifact.handle, payload)

    def _do_apply_uncertainty(self, root_name: str,
                              record: UncertaintyRecord) -> None:
        curve = self.session.graph_main.get_curve(root_name)
        if curve is None:
            return
        store = curve.store
        store.uncertainty_records.append(record)
        store.active_uncertainty_ids.add(record.id)
        self._uncertainty_archive[record.id] = record
        if hasattr(curve.presenter, "set_error_bars"):
            curve.presenter.set_error_bars(store.active_uncertainty_records())
        # Кривая с погрешностями должна слушать изменения filtered_*,
        # чтобы после применения фильтра y_err пересчиталась.
        self._subscribe_curve(root_name)
        store._notify_changed()

    def _do_remove_uncertainty(self, root_name: str,
                               record_id: str) -> None:
        curve = self.session.graph_main.get_curve(root_name)
        if curve is None:
            return
        store = curve.store
        store.uncertainty_records = [
            r for r in store.uncertainty_records if r.id != record_id
        ]
        store.active_uncertainty_ids.discard(record_id)
        if hasattr(curve.presenter, "set_error_bars"):
            curve.presenter.set_error_bars(store.active_uncertainty_records())
        self._maybe_unsubscribe_curve(root_name)
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

    # ------------------------------------------------------------------
    def _payload_for_source(self, payload, index: int, source_id: Optional[str] = None):
        kind = getattr(payload, "kind", None)

        if kind == "annotation":
            pts = list(getattr(payload, "points", []) or [])
            if source_id is not None:
                pts = [p for p in pts
                       if p.get("curve") is None or p.get("curve") == source_id]
            return type(payload)(points=pts, label=payload.label)

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
        if kind == "uncertainty":
            return payload
        return payload