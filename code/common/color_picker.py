from __future__ import annotations
import colorsys
import json
import logging
import os
import re

from PyQt5.QtCore import Qt, QPoint, pyqtSignal
from PyQt5.QtGui import QColor, QCursor, QKeySequence
from PyQt5.QtWidgets import (
    QApplication, QColorDialog, QDialog, QFrame,
    QGridLayout, QGroupBox, QHBoxLayout, QLabel, QMenu, QMessageBox,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from common.undo.manager import SessionUndoManager, UndoCommand

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1
_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def _palette_dir() -> str:
    base = os.getenv("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, "Installation_Controller")


def _palette_path() -> str:
    return os.path.join(_palette_dir(), "color_palette.json")


def _hue_column(hue: float, n: int = 9) -> list:
    mid = n // 2
    column = []
    for i in range(n):
        if i <= mid:
            t = i / max(1, mid)
            v, s = 1.0, 0.15 + t * 0.85
        else:
            t = (i - mid) / max(1, n - 1 - mid)
            v, s = 1.0 - t * 0.85, 1.0
        r, g, b = colorsys.hsv_to_rgb(hue, s, v)
        column.append(f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}")
    return column


def _build_default_palette() -> list:
    columns = [["#ffffff", "#e6e6e6", "#cccccc", "#b3b3b3", "#999999",
                "#808080", "#666666", "#4d4d4d", "#333333", "#1a1a1a", "#000000"]]
    for hue in (0.0, 0.083, 0.145, 0.333, 0.5, 0.583, 0.75):
        columns.append(_hue_column(hue, n=9))
    return columns


def _is_valid_hex(value) -> bool:
    return isinstance(value, str) and _HEX_RE.match(value) is not None


def _parse_color_to_hex(color):
    """Convert anything (QColor / hex-string / rgba-string / tuple) to '#rrggbb'."""
    if color is None:
        return None
    if isinstance(color, QColor):
        return color.name().lower() if color.isValid() else None
    if isinstance(color, str):
        if _is_valid_hex(color):
            return color.lower()
        if color.startswith("rgba(") or color.startswith("rgb("):
            try:
                inner = color[color.index("(") + 1:color.rindex(")")]
                parts = [p.strip() for p in inner.split(",")]
                r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
                return f"#{r:02x}{g:02x}{b:02x}"
            except (ValueError, TypeError, IndexError):
                return None
        return None
    if isinstance(color, (tuple, list)) and len(color) >= 3:
        try:
            r, g, b = int(color[0]), int(color[1]), int(color[2])
            return f"#{r:02x}{g:02x}{b:02x}"
        except (ValueError, TypeError):
            return None
    return None


def _validate_palette_data(data):
    if not isinstance(data, dict):
        return None
    if data.get("schema_version") != SCHEMA_VERSION:
        return None
    columns = data.get("columns")
    if not isinstance(columns, list) or not columns:
        return None
    result = []
    for col in columns:
        if not isinstance(col, list) or not col:
            return None
        cleaned = []
        for c in col:
            if not _is_valid_hex(c):
                return None
            cleaned.append(c.lower())
        result.append(cleaned)
    return result


def load_palette():
    path = _palette_path()
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Не удалось прочитать файл палитры %s: %s", path, exc)
        return None
    result = _validate_palette_data(data)
    if result is None:
        logger.warning("Файл палитры %s повреждён или не соответствует схеме", path)
    return result


def save_palette(columns) -> bool:
    try:
        os.makedirs(_palette_dir(), exist_ok=True)
        data = {"schema_version": SCHEMA_VERSION, "columns": [list(c) for c in columns]}
        with open(_palette_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except OSError as exc:
        logger.warning("Не удалось сохранить палитру: %s", exc)
        return False


def remove_palette_file() -> bool:
    try:
        path = _palette_path()
        if os.path.isfile(path):
            os.remove(path)
        return True
    except OSError as exc:
        logger.warning("Не удалось удалить файл палитры: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Singleton palette
# ---------------------------------------------------------------------------

class ColorPalette:
    _instance: "ColorPalette | None" = None
    MAX_RECENT = 30

    @classmethod
    def instance(cls) -> "ColorPalette":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._recent: list = []
        self._columns = _build_default_palette()
        self._is_custom = False
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        loaded = load_palette()
        if loaded is not None:
            self._columns = loaded
            self._is_custom = True

    @property
    def columns(self) -> list:
        return [list(c) for c in self._columns]

    @property
    def is_custom(self) -> bool:
        return self._is_custom

    def set_columns(self, columns) -> None:
        self._columns = [list(c) for c in columns]
        self._is_custom = True
        save_palette(self._columns)

    def reset_to_default(self) -> None:
        self._columns = _build_default_palette()
        self._is_custom = False
        remove_palette_file()

    def remove_color(self, col_idx: int, color_hex: str) -> bool:
        if not (0 <= col_idx < len(self._columns)):
            return False
        col = self._columns[col_idx]
        if len(col) <= 1:
            return False
        target = color_hex.lower()
        if target in col:
            col.remove(target)
            self._is_custom = True
            save_palette(self._columns)
            return True
        return False

    def replace_color(self, col_idx: int, color_hex: str, new_color_hex: str) -> bool:
        if not (0 <= col_idx < len(self._columns)):
            return False
        col = self._columns[col_idx]
        target = color_hex.lower()
        if target in col:
            col[col.index(target)] = new_color_hex.lower()
            self._is_custom = True
            save_palette(self._columns)
            return True
        return False

    def add_color_to_first(self, color_hex: str) -> None:
        if not self._columns:
            self._columns = [["#cccccc"]]
        self._columns[0].append(color_hex.lower())
        self._is_custom = True
        save_palette(self._columns)

    def add_recent(self, color: QColor) -> None:
        if color is None or not color.isValid():
            return
        hex_color = color.name().lower()
        if hex_color in self._recent:
            self._recent.remove(hex_color)
        self._recent.insert(0, hex_color)
        while len(self._recent) > self.MAX_RECENT:
            self._recent.pop()

    def get_recent(self) -> list:
        return list(self._recent)

    def remove_recent(self, color_hex: str) -> None:
        target = color_hex.lower()
        if target in self._recent:
            self._recent.remove(target)


# ---------------------------------------------------------------------------
# Widgets
# ---------------------------------------------------------------------------

class ColorSwatch(QPushButton):
    right_clicked = pyqtSignal(str, object)

    def __init__(self, color: str, size: int = 16, parent: QWidget | None = None):
        super().__init__(parent)
        self._color = color
        self._size = size
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(color)
        self._update_style(False)

    def color(self) -> str:
        return self._color

    def _update_style(self, hovered: bool) -> None:
        border = "2px solid #4aa3f8" if hovered else "1px solid #888"
        self.setStyleSheet(
            f"QPushButton {{ background-color: {self._color}; "
            f"border: {border}; border-radius: 2px; }}"
        )

    def enterEvent(self, event):
        self._update_style(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._update_style(False)
        super().leaveEvent(event)

    def contextMenuEvent(self, event):
        self.right_clicked.emit(self._color, event.globalPos())
        event.accept()


class PaletteCell(QPushButton):
    CELL_SIZE = 26
    left_clicked = pyqtSignal(int, int)
    right_clicked = pyqtSignal(int, int, object)

    def __init__(self, color: str, col: int, row: int, parent: QWidget | None = None):
        super().__init__(parent)
        self._color = color
        self._col = col
        self._row = row
        self.setFixedSize(self.CELL_SIZE, self.CELL_SIZE)
        self.setCursor(Qt.PointingHandCursor)
        self._update_style()

    def _update_style(self) -> None:
        self.setStyleSheet(
            f"QPushButton {{ background-color: {self._color}; "
            f"border: 1px solid #888; border-radius: 2px; }}"
        )
        self.setToolTip(self._color)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.left_clicked.emit(self._col, self._row)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        self.right_clicked.emit(self._col, self._row, event.globalPos())
        event.accept()


# ---------------------------------------------------------------------------
# Undo command
# ---------------------------------------------------------------------------

class _PaletteStateCommand(UndoCommand):
    def __init__(self, editor: "PaletteEditor", old_state, new_state, text: str):
        self._editor = editor
        self._old_state = [list(c) for c in old_state]
        self._new_state = [list(c) for c in new_state]
        self._text = text

    def text(self) -> str:
        return self._text

    def undo(self) -> None:
        self._editor._apply_state(self._old_state)

    def redo(self) -> None:
        self._editor._apply_state(self._new_state)


# ---------------------------------------------------------------------------
# In-use colors collector
# ---------------------------------------------------------------------------

def _collect_in_use_colors() -> list:
    result: list = []
    try:
        for w in QApplication.topLevelWidgets():
            install_ctrl = getattr(w, "_install_ctrl", None)
            if install_ctrl is not None:
                for dev_name, dev in getattr(install_ctrl, "dict_active_device_class", {}).items():
                    hex_c = _parse_color_to_hex(getattr(dev, "main_color", None))
                    if hex_c:
                        result.append((f"Прибор: {dev_name}", hex_c))
            session_ctrl = getattr(w, "_session_ctrl", None)
            if session_ctrl is not None:
                for _sid, sess in getattr(session_ctrl, "graph_sessions", {}).items():
                    try:
                        curves = sess.graph_main.get_curves()
                    except Exception:
                        continue
                    for root_name, curve in curves.items():
                        style = getattr(curve, "saved_style", None)
                        if style is None:
                            continue
                        hex_c = _parse_color_to_hex(getattr(style, "color", None))
                        if not hex_c:
                            continue
                        name = getattr(curve, "curve_name", None) or root_name
                        result.append((f"Кривая: {name}", hex_c))
    except Exception:
        logger.exception("Ошибка сбора цветов в использовании")
    return result


# ---------------------------------------------------------------------------
# Palette editor
# ---------------------------------------------------------------------------

class PaletteEditor(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Палитра цветов")
        self.resize(800, 600)
        self.setSizeGripEnabled(True)

        self._initial_columns = [list(c) for c in ColorPalette.instance().columns]
        self._columns = [list(c) for c in self._initial_columns]
        self._cells: dict = {}
        self._undo = SessionUndoManager(parent=self)

        self._build_ui()
        self._rebuild()
        self._update_buttons()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Палитра цветов", self)
        f = title.font()
        f.setPointSize(13)
        f.setBold(True)
        title.setFont(f)
        layout.addWidget(title)

        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._grid_container = QWidget()
        self._grid = QGridLayout(self._grid_container)
        self._grid.setSpacing(2)
        self._grid.setContentsMargins(8, 8, 8, 8)
        self._grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._scroll.setWidget(self._grid_container)
        layout.addWidget(self._scroll, 1)

        hints = QLabel(
            "Подсказки:\n"
            "· клик по ячейке — изменить цвет\n"
            "· правый клик по ячейке — удалить, вставить ниже, заменить\n"
            "· правый клик по заголовку столбца — удалить столбец",
            self,
        )
        hints.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(hints)

        col_row = QHBoxLayout()
        self._add_col_btn = QPushButton("+ Столбец", self)
        self._add_col_btn.clicked.connect(self._on_add_column)
        self._remove_col_btn = QPushButton("− Столбец", self)
        self._remove_col_btn.clicked.connect(self._on_remove_column)
        col_row.addWidget(self._add_col_btn)
        col_row.addWidget(self._remove_col_btn)
        col_row.addStretch()
        layout.addLayout(col_row)

        self._in_use_group = QGroupBox("Сейчас используется", self)
        self._in_use_layout = QVBoxLayout(self._in_use_group)
        self._in_use_group.setMaximumHeight(180)
        layout.addWidget(self._in_use_group)
        self._populate_in_use()

        bottom = QHBoxLayout()
        self._reset_btn = QPushButton("Сбросить к стандартной", self)
        self._reset_btn.clicked.connect(self._on_reset)
        bottom.addWidget(self._reset_btn)
        bottom.addStretch()
        self._cancel_btn = QPushButton("Отмена", self)
        self._cancel_btn.clicked.connect(self.reject)
        self._save_btn = QPushButton("Сохранить", self)
        self._save_btn.setDefault(True)
        self._save_btn.clicked.connect(self._on_save)
        bottom.addWidget(self._cancel_btn)
        bottom.addWidget(self._save_btn)
        layout.addLayout(bottom)

    def _populate_in_use(self) -> None:
        while self._in_use_layout.count():
            item = self._in_use_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
            sub = item.layout()
            if sub is not None:
                while sub.count():
                    si = sub.takeAt(0)
                    sw = si.widget()
                    if sw is not None:
                        sw.deleteLater()

        items = _collect_in_use_colors()
        if not items:
            self._in_use_group.setVisible(False)
            return
        self._in_use_group.setVisible(True)

        grouped: dict = {}
        for label, color in items:
            grouped.setdefault(color, []).append(label)

        scroll = QScrollArea(self._in_use_group)
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(130)
        content = QWidget()
        cl = QGridLayout(content)
        cl.setSpacing(4)
        row = 0
        for color, labels in grouped.items():
            swatch = QPushButton()
            swatch.setFixedSize(18, 18)
            swatch.setStyleSheet(
                f"QPushButton {{ background-color: {color}; "
                f"border: 1px solid #888; border-radius: 2px; }}"
            )
            swatch.setCursor(Qt.PointingHandCursor)
            swatch.setToolTip(color + "\n" + "\n".join(labels[:10]))
            swatch.clicked.connect(lambda _=False, c=color: self._copy_color(c))
            cl.addWidget(swatch, row, 0)
            text = ", ".join(labels[:3])
            if len(labels) > 3:
                text += " …"
            lbl = QLabel(text)
            lbl.setStyleSheet("color: #ccc; font-size: 11px;")
            cl.addWidget(lbl, row, 1)
            row += 1
        cl.setRowStretch(row, 1)
        scroll.setWidget(content)
        self._in_use_layout.addWidget(scroll)

    def _copy_color(self, color_hex: str) -> None:
        QApplication.clipboard().setText(color_hex)

    def _state_snapshot(self) -> list:
        return [list(c) for c in self._columns]

    def _apply_state(self, state) -> None:
        self._columns = [list(c) for c in state]
        self._rebuild()
        self._update_buttons()

    def _mutate(self, fn, undo_text: str) -> None:
        old = self._state_snapshot()
        fn()
        new = self._state_snapshot()
        if old == new:
            return
        self._undo.push(_PaletteStateCommand(self, old, new, undo_text))
        self._rebuild()
        self._update_buttons()

    def _rebuild(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._cells = {}

        for col_idx in range(len(self._columns)):
            header = QPushButton(str(col_idx + 1), self._grid_container)
            header.setFixedSize(PaletteCell.CELL_SIZE, 20)
            header.setStyleSheet("font-weight: bold; padding: 0px;")
            header.setToolTip(f"Столбец {col_idx + 1}")
            header.setContextMenuPolicy(Qt.CustomContextMenu)
            header.customContextMenuRequested.connect(
                lambda pos, c=col_idx, h=header: self._on_column_menu(c, h.mapToGlobal(pos))
            )
            self._grid.addWidget(header, 0, col_idx)

        for col_idx, column in enumerate(self._columns):
            for row_idx, color in enumerate(column):
                cell = PaletteCell(color, col_idx, row_idx, self._grid_container)
                cell.left_clicked.connect(self._on_cell_left_click)
                cell.right_clicked.connect(self._on_cell_right_click)
                self._grid.addWidget(cell, row_idx + 1, col_idx)
                self._cells[(col_idx, row_idx)] = cell

    def _update_buttons(self) -> None:
        self._remove_col_btn.setEnabled(len(self._columns) > 1)

    def _on_cell_left_click(self, col: int, row: int) -> None:
        if not (0 <= col < len(self._columns)):
            return
        if not (0 <= row < len(self._columns[col])):
            return
        current = self._columns[col][row]
        color = QColorDialog.getColor(QColor(current), self, "Выбор цвета")
        if not color.isValid():
            return
        new_hex = color.name().lower()
        if new_hex == current:
            return

        def mutate():
            self._columns[col][row] = new_hex
        self._mutate(mutate, "Замена цвета ячейки")

    def _on_cell_right_click(self, col: int, row: int, global_pos) -> None:
        if not (0 <= col < len(self._columns)):
            return
        if not (0 <= row < len(self._columns[col])):
            return

        menu = QMenu(self)
        act_replace = menu.addAction("Заменить цвет…")
        act_insert = menu.addAction("Вставить цвет ниже…")
        act_delete = menu.addAction("Удалить цвет")
        act_delete.setEnabled(len(self._columns[col]) > 1)

        chosen = menu.exec_(global_pos)
        if chosen is act_replace:
            self._on_cell_left_click(col, row)
        elif chosen is act_insert:
            color = QColorDialog.getColor(QColor(self._columns[col][row]), self, "Выбор цвета")
            if not color.isValid():
                return
            new_hex = color.name().lower()

            def mutate():
                self._columns[col].insert(row + 1, new_hex)
            self._mutate(mutate, "Вставка цвета")
        elif chosen is act_delete and len(self._columns[col]) > 1:
            def mutate():
                self._columns[col].pop(row)
            self._mutate(mutate, "Удаление цвета")

    def _on_column_menu(self, col: int, global_pos) -> None:
        menu = QMenu(self)
        act_add = menu.addAction("Добавить цвет в конец")
        act_left = menu.addAction("Вставить столбец слева")
        act_right = menu.addAction("Вставить столбец справа")
        act_delete = menu.addAction("Удалить столбец")
        act_delete.setEnabled(len(self._columns) > 1)

        chosen = menu.exec_(global_pos)
        if chosen is act_add:
            color = QColorDialog.getColor(QColor("#cccccc"), self, "Выбор цвета")
            if not color.isValid():
                return
            new_hex = color.name().lower()

            def mutate():
                self._columns[col].append(new_hex)
            self._mutate(mutate, "Добавление цвета в столбец")
        elif chosen in (act_left, act_right):
            color = QColorDialog.getColor(QColor("#cccccc"), self, "Выбор цвета")
            if not color.isValid():
                return
            new_hex = color.name().lower()
            insert_at = col if chosen is act_left else col + 1

            def mutate():
                self._columns.insert(insert_at, [new_hex])
            self._mutate(mutate, "Вставка столбца")
        elif chosen is act_delete and len(self._columns) > 1:
            def mutate():
                self._columns.pop(col)
            self._mutate(mutate, "Удаление столбца")

    def _on_add_column(self) -> None:
        def mutate():
            self._columns.append(["#cccccc"])
        self._mutate(mutate, "Добавление столбца")

    def _on_remove_column(self) -> None:
        if len(self._columns) <= 1:
            return
        ans = QMessageBox.question(
            self, "Удалить столбец",
            f"Удалить последний столбец ({len(self._columns)})?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if ans != QMessageBox.Yes:
            return

        def mutate():
            self._columns.pop()
        self._mutate(mutate, "Удаление столбца")

    def _on_reset(self) -> None:
        ans = QMessageBox.question(
            self, "Сброс палитры",
            "Сбросить палитру к стандартной?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if ans != QMessageBox.Yes:
            return
        default = _build_default_palette()

        def mutate():
            self._columns = [list(c) for c in default]
        self._mutate(mutate, "Сброс к стандартной")

    def _on_save(self) -> None:
        if not self._columns or any(not c for c in self._columns):
            QMessageBox.warning(
                self, "Ошибка",
                "Должен быть хотя бы один столбец и хотя бы один цвет в каждом столбце.",
            )
            return
        if self._columns != self._initial_columns:
            ColorPalette.instance().set_columns(self._columns)
        self.accept()

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Undo):
            self._undo.undo()
            event.accept()
            return
        if event.matches(QKeySequence.Redo):
            self._undo.redo()
            event.accept()
            return
        super().keyPressEvent(event)


# ---------------------------------------------------------------------------
# Popup
# ---------------------------------------------------------------------------

class ColorPickerPopup(QFrame):
    color_selected = pyqtSignal(QColor)
    SWATCH_SIZE = 16

    def __init__(self, initial_color: QColor | None = None,
                 dialog_parent: QWidget | None = None,
                 parent: QWidget | None = None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setFrameShape(QFrame.StyledPanel)
        self._dialog_parent = dialog_parent
        self._initial = QColor(initial_color) if initial_color is not None else QColor(255, 255, 255)
        self._build_ui()

    def _build_ui(self) -> None:
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(0, 0, 0, 0)
        self._outer.setSpacing(0)
        self._content: QWidget | None = None
        self._rebuild_content()

    def _rebuild_content(self) -> None:
        if self._content is not None:
            self._outer.removeWidget(self._content)
            self._content.hide()
            self._content.setParent(None)
            self._content.deleteLater()

        self._content = QWidget(self)
        self._outer.addWidget(self._content)
        layout = QVBoxLayout(self._content)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        palette = ColorPalette.instance()

        recent = palette.get_recent()
        if recent:
            label = QLabel("Недавние:", self._content)
            label.setStyleSheet("font-size: 10px; color: #888;")
            layout.addWidget(label)
            recent_grid = QGridLayout()
            recent_grid.setSpacing(1)
            per_row = 11
            for i, color in enumerate(recent):
                swatch = ColorSwatch(color, self.SWATCH_SIZE, self._content)
                swatch.clicked.connect(lambda _=False, c=color: self._on_color(c))
                swatch.right_clicked.connect(self._on_recent_swatch_menu)
                recent_grid.addWidget(swatch, i // per_row, i % per_row)
            layout.addLayout(recent_grid)
            sep = QFrame(self._content)
            sep.setFrameShape(QFrame.HLine)
            sep.setFrameShadow(QFrame.Sunken)
            layout.addWidget(sep)

        grid = QGridLayout()
        grid.setSpacing(1)
        columns = palette.columns
        for col_idx, column in enumerate(columns):
            for row_idx, color in enumerate(column):
                swatch = ColorSwatch(color, self.SWATCH_SIZE, self._content)
                swatch.clicked.connect(lambda _=False, c=color: self._on_color(c))
                swatch.right_clicked.connect(
                    lambda c, pos, ci=col_idx: self._on_palette_swatch_menu(c, ci, pos)
                )
                grid.addWidget(swatch, row_idx, col_idx)
        layout.addLayout(grid)

        sep2 = QFrame(self._content)
        sep2.setFrameShape(QFrame.HLine)
        sep2.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep2)

        bottom_row = QHBoxLayout()
        advanced_btn = QPushButton("Дополнительно…", self._content)
        advanced_btn.setCursor(Qt.PointingHandCursor)
        advanced_btn.clicked.connect(self._on_advanced)
        bottom_row.addWidget(advanced_btn, 1)

        gear_btn = QPushButton("⚙", self._content)
        gear_btn.setFixedSize(26, 26)
        gear_btn.setCursor(Qt.PointingHandCursor)
        gear_btn.setToolTip("Редактировать палитру…")
        gear_btn.clicked.connect(self._on_edit_palette)
        bottom_row.addWidget(gear_btn, 0)
        layout.addLayout(bottom_row)

        self.adjustSize()

    def _parent_for_dialogs(self) -> QWidget | None:
        if self._dialog_parent is not None:
            return self._dialog_parent.window()
        return None

    def _on_color(self, color_hex: str) -> None:
        color = QColor(color_hex)
        self._initial = color
        ColorPalette.instance().add_recent(color)
        self.color_selected.emit(color)
        self.close()

    def _on_advanced(self) -> None:
        parent = self._dialog_parent if self._dialog_parent is not None else self
        color = QColorDialog.getColor(self._initial, parent, "Выбор цвета")
        if color.isValid():
            self._initial = color
            ColorPalette.instance().add_recent(color)
            self.color_selected.emit(color)
        self.close()

    def _on_edit_palette(self) -> None:
        editor = PaletteEditor(self._parent_for_dialogs())
        if editor.exec_() == QDialog.Accepted:
            self._rebuild_content()

    def _on_palette_swatch_menu(self, color_hex: str, col_idx: int, global_pos) -> None:
        palette = ColorPalette.instance()
        columns = palette.columns
        can_remove = col_idx < len(columns) and len(columns[col_idx]) > 1

        menu = QMenu(self)
        act_remove = menu.addAction("Убрать из палитры")
        act_remove.setEnabled(can_remove)
        act_replace = menu.addAction("Заменить цвет…")

        chosen = menu.exec_(global_pos)
        if chosen is act_remove and can_remove:
            palette.remove_color(col_idx, color_hex)
            self._rebuild_content()
        elif chosen is act_replace:
            new_color = QColorDialog.getColor(
                QColor(color_hex), self._parent_for_dialogs(), "Замена цвета"
            )
            if not new_color.isValid():
                return
            new_hex = new_color.name().lower()
            palette.replace_color(col_idx, color_hex, new_hex)
            self._initial = new_color
            ColorPalette.instance().add_recent(new_color)
            self.color_selected.emit(new_color)
            self.close()

    def _on_recent_swatch_menu(self, color_hex: str, global_pos) -> None:
        palette = ColorPalette.instance()
        menu = QMenu(self)
        act_pin = menu.addAction("Закрепить в палитре")
        act_remove = menu.addAction("Убрать из недавних")

        chosen = menu.exec_(global_pos)
        if chosen is act_pin:
            palette.add_color_to_first(color_hex)
            self._rebuild_content()
        elif chosen is act_remove:
            palette.remove_recent(color_hex)
            self._rebuild_content()

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        act_add = menu.addAction("Добавить цвет в палитру…")
        menu.addSeparator()
        act_edit = menu.addAction("Редактировать палитру…")
        act_reset = menu.addAction("Сбросить к стандартной")

        chosen = menu.exec_(event.globalPos())
        if chosen is act_add:
            color = QColorDialog.getColor(
                self._initial, self._parent_for_dialogs(), "Добавить цвет"
            )
            if color.isValid():
                ColorPalette.instance().add_color_to_first(color.name().lower())
                self._rebuild_content()
        elif chosen is act_edit:
            self._on_edit_palette()
        elif chosen is act_reset:
            ans = QMessageBox.question(
                self, "Сброс палитры",
                "Сбросить палитру к стандартной? Действие нельзя отменить",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if ans == QMessageBox.Yes:
                ColorPalette.instance().reset_to_default()
                self._rebuild_content()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def pick_color(anchor_widget: QWidget | None, initial_color, on_color_selected,
               parent: QWidget | None = None) -> ColorPickerPopup:
    if isinstance(initial_color, QColor):
        initial = QColor(initial_color)
    elif isinstance(initial_color, str):
        initial = QColor(initial_color)
        if not initial.isValid():
            initial = QColor(255, 255, 255)
    else:
        initial = QColor(255, 255, 255)

    popup = ColorPickerPopup(initial, dialog_parent=parent, parent=parent)
    popup.color_selected.connect(on_color_selected)
    popup.adjustSize()

    if anchor_widget is not None:
        pos = anchor_widget.mapToGlobal(QPoint(0, anchor_widget.height()))
        screen = anchor_widget.screen()
    else:
        pos = QCursor.pos() + QPoint(10, 10)
        screen = None

    if screen is not None:
        avail = screen.availableGeometry()
        size = popup.size()
        x, y = pos.x(), pos.y()
        if x + size.width() > avail.right():
            x = avail.right() - size.width()
        if y + size.height() > avail.bottom():
            if anchor_widget is not None:
                y = anchor_widget.mapToGlobal(QPoint(0, 0)).y() - size.height()
            else:
                y = avail.bottom() - size.height()
            if y < avail.top():
                y = avail.top()
        if x < avail.left():
            x = avail.left()
        pos = QPoint(x, y)

    popup.move(pos)
    popup.show()
    return popup