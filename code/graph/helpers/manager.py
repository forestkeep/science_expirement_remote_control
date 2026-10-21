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
        helper = HelperInstance(helper_type=helper_type, params=params or {})
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
    