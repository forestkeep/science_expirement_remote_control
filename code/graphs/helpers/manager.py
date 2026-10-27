import logging
from typing import List, Optional
from PyQt5.QtCore import QObject, pyqtSignal
from .models import HelperInstance
from .renderers import remove_helper, create_helper

logger = logging.getLogger(__name__)

class HelperManager(QObject):
    helpers_changed = pyqtSignal()
    helper_added = pyqtSignal(object)
    helper_removed = pyqtSignal(str)

    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.graph_view = session.graph_main.graphView
        self._helpers: List[HelperInstance] = []

    def add_helper(self, helper_type: str, params: Optional[dict] = None) -> Optional[HelperInstance]:
        from .renderers import create_helper
        # Получаем текущий пресет из графика
        preset = {}
        if hasattr(self.session.graph_main, "graphView"):
            gv = self.session.graph_main.graphView
            if hasattr(gv, "preset_styles") and gv.preset_styles:
                preset = gv.preset_styles[0]  # можно хранить активный пресет, пока берём первый

        merged_params = {}
        # Применяем стили хелперов из пресета, если пользователь не задал свои
        if "helper_line_color" in preset:
            merged_params["color"] = preset["helper_line_color"]
        if "helper_line_width" in preset:
            merged_params["width"] = preset["helper_line_width"]
        if "helper_text_color" in preset:
            merged_params["text_color"] = preset["helper_text_color"]
        if "helper_font_size" in preset:
            merged_params["font_size"] = preset["helper_font_size"]
        if "helper_marker_color" in preset:
            merged_params["marker_color"] = preset["helper_marker_color"]

        if params:
            merged_params.update(params)  # пользовательские параметры имеют приоритет

        helper = HelperInstance(helper_type=helper_type, params=merged_params)
        items = create_helper(self, helper)
        if not items:
            return None
        helper.items = items
        self._helpers.append(helper)
        self.helper_added.emit(helper)
        self.helpers_changed.emit()
        return helper

    def remove_helper(self, helper_id: str) -> None:
        from .renderers import remove_helper
        for h in self._helpers:
            if h.id == helper_id:
                remove_helper(self, h)
                self._helpers.remove(h)
                self.helper_removed.emit(helper_id)
                self.helpers_changed.emit()
                return

    def remove_all(self) -> None:
        for h in list(self._helpers):
            self.remove_helper(h.id)

    def get_helpers(self) -> List[HelperInstance]:
        return list(self._helpers)

    def set_visible(self, helper_id: str, visible: bool) -> None:
        for h in self._helpers:
            if h.id == helper_id:
                h.visible = visible
                for item in h.items:
                    item.setVisible(visible)
                self.helpers_changed.emit()
                return

    def update_params(self, helper_id: str, params: dict) -> None:
        for h in self._helpers:
            if h.id == helper_id:
                remove_helper(self, h)
                h.params.update(params)
                h.items = create_helper(self, h) or []
                for item in h.items:
                    try:
                        item.setVisible(h.visible)
                    except Exception:
                        pass
                self.helpers_changed.emit()
                return
    