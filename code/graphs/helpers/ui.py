from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QColorDialog, QLabel, QFormLayout, QGroupBox, QScrollArea,
    QCheckBox, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit,
    QToolButton, QApplication,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from common.undo.manager import UndoCommand


HELPER_TITLES = {
    "cursors":   "Курсоры (ΔX/ΔY)",
    "ruler":     "Линейка",
    "text":      "Текстовая метка",
    "arrow":     "Стрелка-выноска",
    "pin":       "Пин",
    "vline":     "Вертикальная линия",
    "hline":     "Горизонтальная линия",
    "threshold": "Пороговая линия",
    "band":      "Полоса",
}

_STYLES = [("solid", "Сплошная"), ("dash", "Штрих"),
           ("dot", "Точки"), ("dashdot", "Штрих-точка")]

_SYMBOLS = ["o", "s", "t", "d", "+", "x", "star", "p", "h"]

class ChangeHelpersColorCommand(UndoCommand):
    def __init__(self, manager, changes):
        self.manager = manager
        self.changes = list(changes)

    def text(self):
        return QApplication.translate("GraphWindow", "Изменение цвета хелперов")

    def redo(self):
        for helper_id, _old, new in self.changes:
            self.manager.update_params(helper_id, {"color": new})

    def undo(self):
        for helper_id, old, _new in self.changes:
            self.manager.update_params(helper_id, {"color": old})


class HelperTab(QWidget):
    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self._collapsed = set()
        self._cards = []
        self._build_ui()
        self.manager.helpers_changed.connect(self._rebuild_list)
        self._rebuild_list()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)

        create_group = QGroupBox("Добавить")
        cg = QVBoxLayout(create_group)
        cg.setContentsMargins(4, 4, 4, 4)
        cg.setSpacing(2)
        for helper_type, title in HELPER_TITLES.items():
            btn = QPushButton(title)
            btn.clicked.connect(
                lambda _=False, ht=helper_type: self.manager.add_helper(ht)
            )
            cg.addWidget(btn)
        outer.addWidget(create_group)

        list_group = QGroupBox("Активные хелперы")
        lg = QVBoxLayout(list_group)
        lg.setContentsMargins(0, 4, 0, 4)

        tools_row = QHBoxLayout()
        self.btn_collapse_all = QPushButton("Свернуть все")
        self.btn_collapse_all.clicked.connect(lambda: self._set_all_expanded(False))
        self.btn_expand_all = QPushButton("Развернуть все")
        self.btn_expand_all.clicked.connect(lambda: self._set_all_expanded(True))
        self.btn_group_color = QPushButton("Цвет всех")
        self.btn_group_color.setToolTip("Изменить цвет всех применённых хелперов")
        self.btn_group_color.clicked.connect(self._choose_group_color)

        tools_row.addWidget(self.btn_collapse_all)
        tools_row.addWidget(self.btn_expand_all)
        tools_row.addWidget(self.btn_group_color)
        tools_row.addStretch()
        lg.addLayout(tools_row)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.content = QWidget()
        self.form = QVBoxLayout(self.content)
        self.form.setContentsMargins(2, 2, 2, 2)
        self.form.setSpacing(6)
        self.scroll.setWidget(self.content)
        lg.addWidget(self.scroll, 1)

        clear_btn = QPushButton("Очистить все")
        clear_btn.clicked.connect(self.manager.remove_all)
        lg.addWidget(clear_btn)

        outer.addWidget(list_group, 1)

    def _set_all_expanded(self, expanded: bool):
        for _helper_id, toggle in self._cards:
            toggle.setChecked(expanded)

    def _choose_group_color(self):
        c = QColorDialog.getColor()
        if not c.isValid():
            return

        changes = []
        for helper in self.manager.get_helpers():
            if "color" not in helper.params:
                continue
            old = helper.params.get("color", "#ffffff")
            new = c.name()
            if old != new:
                changes.append((helper.id, old, new))

        if not changes:
            return

        cmd = ChangeHelpersColorCommand(self.manager, changes)
        session = getattr(self.manager, "session", None)
        undo_manager = getattr(session, "undo_manager", None)

        if undo_manager is not None and not undo_manager.is_applying:
            undo_manager.push(cmd, execute=True)
        else:
            cmd.redo()

    def _rebuild_list(self):
        self._cards = []
        while self.form.count():
            item = self.form.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        helpers = self.manager.get_helpers()
        if not helpers:
            lbl = QLabel("Хелперов нет")
            lbl.setAlignment(Qt.AlignCenter)
            self.form.addWidget(lbl)
        else:
            for helper in helpers:
                self.form.addWidget(self._build_helper_group(helper))

        self.form.addStretch()

    def _build_helper_group(self, helper):
        title = HELPER_TITLES.get(helper.helper_type, helper.helper_type)
        card = QGroupBox(title)
        card.setStyleSheet(
            "QGroupBox {"
            " border: 1px solid #555;"
            " border-radius: 4px;"
            " margin-top: 10px;"
            " padding-top: 6px;"
            " background-color: rgba(255, 255, 255, 8);"
            "}"
            "QGroupBox::title {"
            " subcontrol-origin: margin;"
            " left: 8px;"
            " padding: 0 4px;"
            "}"
        )

        outer = QVBoxLayout(card)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(4)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        toggle = QToolButton()
        toggle.setCheckable(True)
        expanded = helper.id not in self._collapsed
        toggle.setChecked(expanded)
        toggle.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)
        toggle.setAutoRaise(True)
        toggle.setFixedSize(18, 18)
        header.addWidget(toggle)

        cb = QCheckBox("Видим")
        cb.setChecked(helper.visible)
        cb.stateChanged.connect(
            lambda st, hid=helper.id: self.manager.set_visible(hid, st != 0)
        )
        header.addWidget(cb)
        header.addStretch()

        del_btn = QPushButton("×")
        del_btn.setFixedWidth(24)
        del_btn.clicked.connect(
            lambda _=False, hid=helper.id: self.manager.remove_helper(hid)
        )
        header.addWidget(del_btn)

        outer.addLayout(header)

        content = QWidget()
        f = QFormLayout(content)
        f.setLabelAlignment(Qt.AlignLeft)
        outer.addWidget(content)

        def _on_toggle(checked: bool):
            content.setVisible(checked)
            toggle.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
            if checked:
                self._collapsed.discard(helper.id)
            else:
                self._collapsed.add(helper.id)

        toggle.toggled.connect(_on_toggle)
        content.setVisible(expanded)

        color = helper.params.get("color", "#ffffff")
        color_btn = QPushButton(color)
        color_btn.setStyleSheet(f"background-color: {color}; padding: 2px;")

        def choose_color(_checked=False, h=helper):
            c = QColorDialog.getColor(QColor(h.params.get("color", "#ffffff")))
            if c.isValid():
                self.manager.update_params(h.id, {"color": c.name()})

        color_btn.clicked.connect(choose_color)
        f.addRow("Цвет:", color_btn)

        t = helper.helper_type

        if t in ("cursors", "ruler", "arrow", "vline", "hline", "threshold", "band"):
            w = QSpinBox()
            w.setRange(1, 10)
            w.setValue(int(helper.params.get("width", 1)))
            w.valueChanged.connect(
                lambda v, hid=helper.id:
                    self.manager.update_params(hid, {"width": int(v)})
            )
            f.addRow("Толщина:", w)

            style = QComboBox()
            for key, label in _STYLES:
                style.addItem(label, key)
            idx = style.findData(helper.params.get("style", "solid"))
            if idx >= 0:
                style.setCurrentIndex(idx)
            style.currentIndexChanged.connect(
                lambda _i, hid=helper.id, sw=style:
                    self.manager.update_params(hid, {"style": sw.currentData()})
            )
            f.addRow("Стиль:", style)

        if t in ("text", "arrow", "pin"):
            le = QLineEdit(helper.params.get("text", ""))
            le.editingFinished.connect(
                lambda h=helper, e=le:
                    self.manager.update_params(h.id, {"text": e.text()})
            )
            f.addRow("Текст:", le)

        if t == "arrow":
            ts = QSpinBox()
            ts.setRange(6, 72)
            ts.setValue(int(helper.params.get("text_size", 12)))
            ts.setToolTip("Размер шрифта текста выноски")
            ts.valueChanged.connect(
                lambda v, hid=helper.id:
                    self.manager.update_params(hid, {"text_size": int(v)})
            )
            f.addRow("Размер шрифта:", ts)

            ah = QSpinBox()
            ah.setRange(4, 60)
            ah.setValue(int(helper.params.get("arrow_size", 12)))
            ah.setToolTip("Длина наконечника стрелки")
            ah.valueChanged.connect(
                lambda v, hid=helper.id:
                    self.manager.update_params(hid, {"arrow_size": int(v)})
            )
            f.addRow("Размер стрелки:", ah)

            arr_style = QComboBox()
            for key, label in (
                ("default", "Обычная"),
                ("narrow",  "Узкая"),
                ("wide",    "Широкая"),
                ("sharp",   "Острая"),
            ):
                arr_style.addItem(label, key)
            idx = arr_style.findData(helper.params.get("arrow_style", "default"))
            if idx >= 0:
                arr_style.setCurrentIndex(idx)
            arr_style.currentIndexChanged.connect(
                lambda _i, hid=helper.id, sw=arr_style:
                    self.manager.update_params(hid, {"arrow_style": sw.currentData()})
            )
            f.addRow("Стиль стрелки:", arr_style)

        if t == "text":
            fs = QSpinBox()
            fs.setRange(6, 72)
            fs.setValue(int(helper.params.get("font_size", 12)))
            fs.setToolTip("Размер шрифта подписи")
            fs.valueChanged.connect(
                lambda v, hid=helper.id:
                    self.manager.update_params(hid, {"font_size": int(v)})
            )
            f.addRow("Размер шрифта:", fs)

        if t == "pin":
            size = QSpinBox()
            size.setRange(4, 40)
            size.setValue(int(helper.params.get("size", 12)))
            size.valueChanged.connect(
                lambda v, hid=helper.id:
                    self.manager.update_params(hid, {"size": int(v)})
            )
            f.addRow("Размер маркера:", size)

            ts = QSpinBox()
            ts.setRange(6, 72)
            ts.setValue(int(helper.params.get("text_size", 12)))
            ts.setToolTip("Размер шрифта подписи пина")
            ts.valueChanged.connect(
                lambda v, hid=helper.id:
                    self.manager.update_params(hid, {"text_size": int(v)})
            )
            f.addRow("Размер шрифта:", ts)

            sym = QComboBox()
            sym.addItems(_SYMBOLS)
            idx = sym.findText(helper.params.get("symbol", "o"))
            if idx >= 0:
                sym.setCurrentIndex(idx)
            sym.currentIndexChanged.connect(
                lambda _i, hid=helper.id, sw=sym:
                    self.manager.update_params(hid, {"symbol": sw.currentText()})
            )
            f.addRow("Символ:", sym)

            desc_edit = QTextEdit(helper.params.get("description", ""))
            desc_edit.setPlaceholderText(
                "Заметка. Появится во всплывающей подсказке при наведении на метку."
            )
            desc_edit.setMaximumHeight(80)
            desc_edit.setToolTip(
                "Текст описания будет показан как tooltip при наведении курсора на метку."
            )
            f.addRow("Описание:", desc_edit)

            save_desc_btn = QPushButton("Сохранить описание")
            save_desc_btn.setToolTip("Изменения описания применяются только по этой кнопке")

            def _save_description(_checked=False, h=helper, e=desc_edit):
                new_text = e.toPlainText()
                if new_text == h.params.get("description", ""):
                    return
                self.manager.update_params(h.id, {"description": new_text})

            save_desc_btn.clicked.connect(_save_description)
            f.addRow(save_desc_btn)

        if t == "threshold":
            prefix = QLineEdit(helper.params.get("prefix", "Порог"))
            prefix.editingFinished.connect(
                lambda h=helper, e=prefix:
                    self.manager.update_params(h.id, {"prefix": e.text()})
            )
            f.addRow("Подпись:", prefix)

            direction = QComboBox()
            for key, label in (
                ("off",   "Без заливки"),
                ("above", "Залить выше порога"),
                ("below", "Залить ниже порога"),
                ("both",  "Залить обе зоны"),
            ):
                direction.addItem(label, key)
            idx = direction.findData(helper.params.get("direction", "off"))
            if idx >= 0:
                direction.setCurrentIndex(idx)
            direction.currentIndexChanged.connect(
                lambda _i, hid=helper.id, sw=direction:
                    self.manager.update_params(hid, {"direction": sw.currentData()})
            )
            f.addRow("Заливка:", direction)

            alpha = QDoubleSpinBox()
            alpha.setRange(0.0, 1.0)
            alpha.setSingleStep(0.05)
            alpha.setValue(float(helper.params.get("fill_alpha", 0.15)))
            alpha.valueChanged.connect(
                lambda v, hid=helper.id:
                    self.manager.update_params(hid, {"fill_alpha": float(v)})
            )
            f.addRow("Прозрачность заливки:", alpha)

            cnt = QCheckBox("Показывать число точек ▲/▼")
            cnt.setChecked(bool(helper.params.get("show_count", False)))
            cnt.stateChanged.connect(
                lambda st, hid=helper.id:
                    self.manager.update_params(hid, {"show_count": st != 0})
            )
            f.addRow(cnt)

        if t in ("cursors", "band"):
            orient = QComboBox()
            orient.addItem("Вертикальная", "vertical")
            orient.addItem("Горизонтальная", "horizontal")
            idx = orient.findData(helper.params.get("orientation", "vertical"))
            if idx >= 0:
                orient.setCurrentIndex(idx)
            orient.currentIndexChanged.connect(
                lambda _i, hid=helper.id, sw=orient:
                    self.manager.update_params(hid, {"orientation": sw.currentData()})
            )
            f.addRow("Ориентация:", orient)

        if t == "band":
            alpha = QDoubleSpinBox()
            alpha.setRange(0.0, 1.0)
            alpha.setSingleStep(0.05)
            alpha.setValue(float(helper.params.get("alpha", 0.25)))
            alpha.valueChanged.connect(
                lambda v, hid=helper.id:
                    self.manager.update_params(hid, {"alpha": float(v)})
            )
            f.addRow("Прозрачность:", alpha)

            reset_pos = QPushButton("Сбросить позицию значения")
            reset_pos.clicked.connect(
                lambda _=False, hid=helper.id:
                    self.manager.update_params(hid, {
                        "_text_dragged": False,
                        "text_pos": None,
                    })
            )
            f.addRow(reset_pos)

        if t in ("cursors", "ruler", "vline", "hline", "threshold", "band"):
            fmt = QLineEdit(str(helper.params.get("format", ".4g")))
            fmt.setToolTip("Формат числа (например .4g, .2f, .0e)")
            fmt.editingFinished.connect(
                lambda h=helper, e=fmt:
                    self.manager.update_params(h.id, {"format": e.text()})
            )
            f.addRow("Формат числа:", fmt)

        if t in ("cursors", "ruler", "vline", "hline", "threshold", "band"):
            show_lbl = QCheckBox("Показывать значение")
            show_lbl.setChecked(bool(helper.params.get("show_label", True)))
            show_lbl.stateChanged.connect(
                lambda st, hid=helper.id:
                    self.manager.update_params(hid, {"show_label": st != 0})
            )
            f.addRow(show_lbl)

        if t == "cursors":
            for key, label, default in (
                ("show_line1_label", "Показывать значение линии 1", True),
                ("show_line2_label", "Показывать значение линии 2", True),
            ):
                cb = QCheckBox(label)
                cb.setChecked(bool(helper.params.get(key, default)))
                cb.stateChanged.connect(
                    lambda st, hid=helper.id, k=key:
                        self.manager.update_params(hid, {k: st != 0})
                )
                f.addRow(cb)

            for key, label, default in (
                ("show_dx",   "Показывать ΔX", True),
                ("show_dy",   "Показывать ΔY", False),
                ("show_dist", "Показывать расстояние", False),
            ):
                cb = QCheckBox(label)
                cb.setChecked(bool(helper.params.get(key, default)))
                cb.stateChanged.connect(
                    lambda st, hid=helper.id, k=key:
                        self.manager.update_params(hid, {k: st != 0})
                )
                f.addRow(cb)

            reset_pos = QPushButton("Сбросить позицию Δ")
            reset_pos.clicked.connect(
                lambda _=False, hid=helper.id:
                    self.manager.update_params(hid, {
                        "_text_dragged": False,
                        "text_pos": None,
                    })
            )
            f.addRow(reset_pos)

        elif t == "ruler":
            info = QLabel("Показывает ΔX и ΔY одновременно")
            info.setStyleSheet("color: #888;")
            info.setWordWrap(True)
            f.addRow(info)

        self._cards.append((helper.id, toggle))
        return card