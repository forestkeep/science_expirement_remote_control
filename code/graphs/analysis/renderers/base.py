"""Базовый интерфейс рендерера."""
from __future__ import annotations

from abc import ABC, abstractmethod


class BaseRenderer(ABC):
    @abstractmethod
    def render(self, artifact, is_preview: bool = False):
        ...

    @abstractmethod
    def update(self, handle, payload) -> None:
        ...

    @abstractmethod
    def remove(self, handle) -> None:
        ...

    @abstractmethod
    def set_visible(self, handle, visible: bool) -> None:
        ...

def apply_main_graph_style(session, plot_widget) -> None:
    """Скопировать внешний вид основного графика на новый PatchedPlotWidget.

    Нужен, чтобы attached-панели (производная, интеграл) и domain-вкладки
    (спектр, автокорреляция) строились в том же стиле, что и основной график,
    даже если пользователь менял фон/сетку/шрифты до их создания.
    """
    import logging
    logger = logging.getLogger(__name__)
    try:
        from graphs.hdf5_io.utils import extract_plot_widget_settings
        from graphs.hdf5_io.adapters import HDF5ToProjectAdapter
        from graphs.hdf5_io.models import FieldSettings
    except Exception:
        logger.exception("apply_main_graph_style: imports failed")
        return

    main = getattr(getattr(session, "graph_main", None), "graphView", None)
    if main is None:
        return
    try:
        settings = FieldSettings()
        settings.graph_field = extract_plot_widget_settings(main)
        HDF5ToProjectAdapter().apply_graph_settings(plot_widget, settings)
    except Exception:
        logger.exception("apply_main_graph_style failed")


def artifact_display_suffix(artifact) -> str:
    """Человекочитаемое имя инструмента для подписи в легенде.

    Берётся из реестра (локализованный title), с fallback на последний
    компонент tool_id. Пример: 'diff.derivative' → 'Производная'.
    """
    try:
        from ..registry import AnalysisToolRegistry
        from ..models import tr_analysis
        desc = AnalysisToolRegistry.instance().get(artifact.tool_id)
        if desc is not None:
            return tr_analysis(desc.title_key)
    except Exception:
        pass
    return artifact.tool_id.split(".")[-1] if artifact.tool_id else "?"


def artifact_legend_name(session, artifact, curve_id) -> str:
    """«Имя кривой ▸ Название инструмента» для подписи в легенде."""
    curve = session.graph_main.get_curve(curve_id) if curve_id else None
    base = curve.curve_name if curve else (curve_id or "?")
    return f"{base} ▸ {artifact_display_suffix(artifact)}"