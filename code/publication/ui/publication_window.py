from __future__ import annotations

from PyQt5.QtWidgets import QMainWindow, QWidget

from ..model.figure_model import FigureSpec
from .publication_window_parts import (
    PublicationWidgetCoreMixin,
    PublicationWidgetPinsMixin,
    PublicationWidgetSelectionMixin,
    PublicationWidgetSlotsMixin,
    PublicationWidgetAnnotationsMixin,
    PublicationWidgetPanelsMixin,
)


class PublicationWidget(
    PublicationWidgetCoreMixin,
    PublicationWidgetPinsMixin,
    PublicationWidgetSelectionMixin,
    PublicationWidgetSlotsMixin,
    PublicationWidgetAnnotationsMixin,
    PublicationWidgetPanelsMixin,
    QWidget,
):
    """Публикационный модуль целиком.

    Реализация разделена на миксины в publication_window_parts:
      * core        — __init__, UI, тулбар, статус, рендер;
      * pins        — 📌-закрепления overrides;
      * selection   — выделение, геометрия, оси, легенда;
      * slots       — слоты кривых и CurveInspector;
      * annotations — presentation-аннотации;
      * panels      — панели, шаблоны, валидация, экспорт, файлы.
    """

    pass


class PublicationWindow(QMainWindow):
    """Окно-обёртка публикационного модуля.

    app/main_window.py ожидает у страницы публикации метод widget(),
    возвращающий PublicationWidget. Поэтому атрибут называется
    _publication_widget, а widget() — метод.
    """

    def __init__(self, session_controller, spec: FigureSpec = None, parent=None):
        super().__init__(parent)
        self.session_controller = session_controller
        self._publication_widget = PublicationWidget(
            session_controller=session_controller,
            spec=spec,
            parent=self,
        )
        self.setCentralWidget(self._publication_widget)
        self.setWindowTitle("Публикация")
        self.resize(1400, 900)

    def widget(self):
        """Совместимость с UnifiedMainWindow._pub_widget()."""
        return self._publication_widget

    def save_to_file(self, path: str):
        return self._publication_widget.save_to_file(path)

    def load_from_file(self, path: str):
        return self._publication_widget.load_from_file(path)