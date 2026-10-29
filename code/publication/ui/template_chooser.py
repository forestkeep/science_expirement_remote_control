"""Диалог выбора шаблона раскладки панелей с визуальными превью."""
from __future__ import annotations
from typing import Dict, Optional

from PyQt5.QtCore import Qt, QRectF, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import (
    QButtonGroup, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
    QFrame, QGridLayout, QLabel, QMessageBox, QRadioButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from ..layouts import (
    BUILTIN_TEMPLATES, LayoutTemplate, apply_template, preview_counts,
)
from ..model.figure_model import FigureSpec


class TemplatePreview(QWidget):
    """Кликабельная миниатюра шаблона.

    Рисуется QPainter-ом, поэтому не зависит от иконок/файлов и корректно
    масштабируется под любой DPI. Выбранное состояние подсвечивается
    акцентным цветом.
    """

    clicked = pyqtSignal()

    PADDING = 8

    def __init__(self, template: LayoutTemplate, parent=None):
        super().__init__(parent)
        self.template = template
        self._selected = False
        self._hovered = False
        self.setFixedSize(110, 84)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(f"{template.name} — {template.description}")

    def set_selected(self, value: bool) -> None:
        if self._selected == value:
            return
        self._selected = value
        self.update()

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        try:
            rect = self.rect().adjusted(2, 2, -2, -2)

            if self._selected:
                bg = QColor(42, 130, 218, 60)
                border = QColor("#2a82da")
                border_w = 2
            elif self._hovered:
                bg = QColor(200, 200, 200, 40)
                border = QColor("#888888")
                border_w = 1
            else:
                bg = QColor(0, 0, 0, 0)
                border = QColor("#555555")
                border_w = 1

            p.setBrush(bg)
            p.setPen(QPen(border, border_w))
            p.drawRoundedRect(rect, 4, 4)

            inner = rect.adjusted(self.PADDING, self.PADDING,
                                  -self.PADDING, -self.PADDING)
            iw = max(1.0, float(inner.width()))
            ih = max(1.0, float(inner.height()))
            cw = iw / self.template.cols
            ch = ih / self.template.rows
            gap = 2.0

            cell_color = QColor("#2a82da") if self._selected else QColor("#c8c8c8")
            p.setPen(QPen(cell_color.darker(140), 1))
            p.setBrush(cell_color)
            for (r, c, rs, cs) in self.template.cells:
                x = float(inner.left()) + c * cw + gap * 0.5
                y = float(inner.top()) + r * ch + gap * 0.5
                w = cs * cw - gap
                h = rs * ch - gap
                if w <= 0 or h <= 0:
                    continue
                p.drawRoundedRect(QRectF(x, y, w, h), 2, 2)

            f = QFont()
            f.setPointSize(8)
            p.setFont(f)
            p.setPen(QColor("#e0e0e0") if self._selected else QColor("#888888"))
            label_rect = self.rect().adjusted(0, self.rect().height() - 20, 0, 0)
            p.drawText(label_rect, Qt.AlignHCenter | Qt.AlignVCenter,
                       self.template.name)
        finally:
            p.end()


class TemplateChooserDialog(QDialog):
    """Диалог выбора шаблона раскладки.

    Возвращает управление через accept()/reject(). При успехе
    самостоятельно вызывает apply_template(spec, ...) — так вызывающий
    код не дублирует логику применения.
    """

    def __init__(self, spec: FigureSpec, default_margin: float = 3.0,
                 default_gap: float = 2.0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Раскладка панелей по шаблону")
        self.setModal(True)
        self.resize(720, 620)
        self.spec = spec
        self._selected_template: Optional[LayoutTemplate] = None
        self._previews: Dict[str, TemplatePreview] = {}

        self._build_ui(float(default_margin), float(default_gap))

        # На пустой фигуре «Переложить» бессмысленно — сразу предлагаем «Заменить».
        if not self.spec.panels:
            self._radio_replace.setChecked(True)

        if BUILTIN_TEMPLATES:
            self._on_template_selected(BUILTIN_TEMPLATES[0])

    # ---------------------------------------------------------------- UI
    def _build_ui(self, default_margin: float, default_gap: float) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        hint = QLabel(
            "Выберите шаблон и нажмите «Применить». "
            "«Переложить» сохраняет данные панелей и меняет только их "
            "геометрию; «Заменить» удаляет существующие панели и создаёт "
            "новые пустые."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #888;")
        layout.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        grid = QGridLayout(content)
        grid.setSpacing(6)
        for i, template in enumerate(BUILTIN_TEMPLATES):
            preview = TemplatePreview(template)
            preview.clicked.connect(
                lambda t=template: self._on_template_selected(t)
            )
            self._previews[template.id] = preview
            grid.addWidget(preview, i // 5, i % 5)
        scroll.setWidget(content)
        scroll.setMinimumHeight(220)
        layout.addWidget(scroll, 1)

        params = QFormLayout()
        self.margin_spin = QDoubleSpinBox()
        self.margin_spin.setRange(0.0, 30.0)
        self.margin_spin.setDecimals(1)
        self.margin_spin.setSingleStep(0.5)
        self.margin_spin.setSuffix(" мм")
        self.margin_spin.setValue(default_margin)
        self.margin_spin.valueChanged.connect(self._update_preview_counts)
        params.addRow("Внешнее поле (margin):", self.margin_spin)

        self.gap_spin = QDoubleSpinBox()
        self.gap_spin.setRange(0.0, 20.0)
        self.gap_spin.setDecimals(1)
        self.gap_spin.setSingleStep(0.5)
        self.gap_spin.setSuffix(" мм")
        self.gap_spin.setValue(default_gap)
        self.gap_spin.valueChanged.connect(self._update_preview_counts)
        params.addRow("Зазор между ячейками (gap):", self.gap_spin)
        layout.addLayout(params)

        mode_box = QFrame()
        mode_layout = QVBoxLayout(mode_box)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.addWidget(QLabel("Режим:"))
        self._mode_group = QButtonGroup(self)
        self._radio_reflow = QRadioButton(
            "Переложить — сохранить панели и данные, изменить геометрию"
        )
        self._radio_replace = QRadioButton(
            "Заменить — удалить все панели, создать новые пустые"
        )
        self._radio_reflow.setChecked(True)
        self._mode_group.addButton(self._radio_reflow)
        self._mode_group.addButton(self._radio_replace)
        self._radio_reflow.toggled.connect(self._update_preview_counts)
        self._radio_replace.toggled.connect(self._update_preview_counts)
        mode_layout.addWidget(self._radio_reflow)
        mode_layout.addWidget(self._radio_replace)
        layout.addWidget(mode_box)

        self._status = QLabel("—")
        self._status.setWordWrap(True)
        self._status.setStyleSheet("font-family: monospace; color: #333;")
        layout.addWidget(self._status)

        self._bbox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self._bbox.button(QDialogButtonBox.Ok).setText("Применить")
        self._bbox.button(QDialogButtonBox.Cancel).setText("Отмена")
        self._bbox.accepted.connect(self._on_accept)
        self._bbox.rejected.connect(self.reject)
        layout.addWidget(self._bbox)

    # ---------------------------------------------------------------- selection
    def _on_template_selected(self, template: LayoutTemplate) -> None:
        self._selected_template = template
        for tid, preview in self._previews.items():
            preview.set_selected(tid == template.id)
        self._update_preview_counts()

    def _update_preview_counts(self) -> None:
        if self._selected_template is None:
            self._status.setText("Шаблон не выбран")
            self._refresh_ok_enabled()
            return

        existing, cells, will_lose = preview_counts(
            self.spec, self._selected_template
        )
        reflow = self._radio_reflow.isChecked()
        lines = [
            f"Шаблон «{self._selected_template.name}»: {cells} ячеек.",
            f"В фигуре панелей: {existing}.",
        ]

        if reflow:
            if existing == 0:
                lines.append(
                    "⚠ В фигуре нет панелей — «Переложить» ничего не создаст. "
                    "Переключитесь на «Заменить»."
                )
            elif will_lose > 0:
                lines.append(
                    f"⚠ Не поместится панелей: {will_lose}. Выберите шаблон "
                    f"с большим числом ячеек или режим «Заменить»."
                )
            else:
                lines.append(
                    f"Будет переложено: {existing}. "
                    f"Свободных ячеек: {cells - existing}."
                )
        else:
            lines.append(
                f"Существующие панели будут удалены, создадутся {cells} новых."
            )

        self._status.setText("\n".join(lines))
        self._refresh_ok_enabled()

    def _refresh_ok_enabled(self) -> None:
        ok = self._selected_template is not None
        if ok and self._radio_reflow.isChecked():
            existing, cells, _ = preview_counts(
                self.spec, self._selected_template
            )
            # На пустой фигуре «Переложить» — no-op; блокируем OK.
            if existing == 0 or existing > cells:
                ok = False
        self._bbox.button(QDialogButtonBox.Ok).setEnabled(ok)

    # ---------------------------------------------------------------- apply
    def _on_accept(self) -> None:
        if self._selected_template is None:
            return
        mode = "reflow" if self._radio_reflow.isChecked() else "replace"
        try:
            apply_template(
                self.spec, self._selected_template,
                margin_mm=float(self.margin_spin.value()),
                gap_mm=float(self.gap_spin.value()),
                mode=mode,
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Не удалось применить шаблон", str(exc))
            return
        self.accept()