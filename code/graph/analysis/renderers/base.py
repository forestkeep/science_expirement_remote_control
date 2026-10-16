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
        from graph.hdf5_io.utils import extract_plot_widget_settings
        from graph.hdf5_io.adapters import HDF5ToProjectAdapter
        from graph.hdf5_io.models import FieldSettings
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