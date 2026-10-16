from PyQt5.QtCore import QObject, pyqtSignal

class SelectionModel(QObject):
    """
    Single source of truth for curve selection.

    Curves (CurvePresenter) subscribe to selection_changed and update
    their visuals. The model itself knows nothing about widgets — it
    stores opaque objects.
    """

    selection_changed = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected = []
        self._selected_set = set()

    def select(self, items, additive: bool = False) -> bool:
        if not isinstance(items, (list, tuple)):
            items = [items]
        items = [it for it in items if it is not None]
        if not items:
            return self.clear() if not additive else False

        if additive:
            new_selection = list(self._selected)
            for it in items:
                if it not in self._selected_set:
                    new_selection.append(it)
        else:
            seen, new_selection = set(), []
            for it in items:
                if it not in seen:
                    seen.add(it)
                    new_selection.append(it)

        return self._set_selection(new_selection)

    def add(self, item) -> bool:
        return self.select([item], additive=True)

    def toggle(self, item) -> bool:
        if item in self._selected_set:
            return self.remove(item)
        return self.add(item)

    def remove(self, item) -> bool:
        if item not in self._selected_set:
            return False
        return self._set_selection([it for it in self._selected if it is not item])

    def clear(self) -> bool:
        if not self._selected:
            return False
        return self._set_selection([])

    def current(self) -> list:
        return list(self._selected)

    def is_selected(self, item) -> bool:
        return item in self._selected_set

    def _set_selection(self, new_selection: list) -> bool:
        if new_selection == self._selected:
            return False
        self._selected = new_selection
        self._selected_set = set(new_selection)
        self.selection_changed.emit(list(self._selected))
        return True