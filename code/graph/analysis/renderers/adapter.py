"""Фасад над рендерерами. Контроллер общается только с ним."""
from __future__ import annotations

import logging
from typing import Any, Dict

from ..models import PlacementType
from .attached import AttachedRenderer
from .domain import DomainRenderer
from .overlay import OverlayRenderer

logger = logging.getLogger(__name__)


class AnalysisRendererAdapter:
    def __init__(self, session) -> None:
        self.session = session
        self._overlay = OverlayRenderer(session)
        self._attached = AttachedRenderer(session)
        self._domain = DomainRenderer(session)

    def render(self, artifact, is_preview: bool = False):
        ptype = artifact.placement_type
        if ptype == PlacementType.OVERLAY or ptype == PlacementType.ANNOTATION:
            return self._overlay.render(artifact, is_preview)
        if ptype == PlacementType.ATTACHED:
            return self._attached.render(artifact, is_preview)
        if ptype == PlacementType.DOMAIN:
            return self._domain.render(artifact, is_preview)
        return None

    def update(self, handle, payload) -> None:
        # Определяем рендерер по типу handle
        if handle is None:
            return
        for r in (self._overlay, self._attached, self._domain):
            if self._handle_belongs_to(r, handle):
                r.update(handle, payload)
                return

    def remove(self, handle) -> None:
        if handle is None:
            return
        for r in (self._overlay, self._attached, self._domain):
            try:
                # сбросить сохранённые оригиналы перьев для этих item'ов
                store = getattr(r, "_original_pens", None)
                if store is not None:
                    for item in (handle or []):
                        store.pop(id(item), None)
                r.remove(handle)
            except Exception:
                logger.exception("AnalysisRendererAdapter.remove failed")

    def set_visible(self, handle, visible: bool) -> None:
        if handle is None:
            return
        for r in (self._overlay, self._attached, self._domain):
            try:
                r.set_visible(handle, visible)
            except Exception:
                pass

    # ------------------------------------------------------------------
    @staticmethod
    def _handle_belongs_to(renderer, handle) -> bool:
        if isinstance(handle, list):
            for item in handle:
                if _is_plot_item_in_view(item, renderer):
                    return True
        return False

    def set_highlighted(self, handle, highlighted: bool) -> None:
        """Подсветка/снятие подсветки. Handle принадлежит ровно одному
        рендереру, поэтому диспетчеризуем к нему одному — иначе несколько
        рендереров сохранят/восстановят перо одного и того же item'а и
        перезапишут друг друга.

        Порядок важен: attached/domain — по фактическому владению,
        overlay — fallback (его `_is_plot_item_in_view` всегда True).
        """
        if handle is None:
            return
        for r in (self._attached, self._domain):
            if not hasattr(r, "set_highlighted"):
                continue
            if self._handle_belongs_to(r, handle):
                try:
                    r.set_highlighted(handle, highlighted)
                except Exception:
                    logger.exception("AnalysisRendererAdapter.set_highlighted failed")
                return
        try:
            self._overlay.set_highlighted(handle, highlighted)
        except Exception:
            logger.exception("AnalysisRendererAdapter.set_highlighted failed")


def _is_plot_item_in_view(item, renderer) -> bool:
    # Эвристика: смотрим, в какой коллекции рендерера item хранится
    for info in getattr(renderer, "_panels", {}).values():
        if item in info.get("handles", []):
            return True
    for info in getattr(renderer, "_tabs", {}).values():
        if item in info.get("handles", []):
            return True
    # Overlay не хранит состояний — считаем его дефолтным
    if renderer.__class__.__name__ == "OverlayRenderer":
        return True
    return False