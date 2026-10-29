"""Модель шаблона раскладки панелей.

Ячейки задаются в единицах сетки (row, col, rowspan, colspan) — как в CSS
Grid / HTML-таблицах. Это самая компактная и гибкая форма: один шаблон
выражает и «2×2 сетку», и «большая слева + две малые справа», не дублируя
координаты.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple


Cell = Tuple[int, int, int, int]   # (row, col, rowspan, colspan)
Rect = Tuple[float, float, float, float]  # (x_mm, y_mm, w_mm, h_mm)


@dataclass(frozen=True)
class LayoutTemplate:
    id: str
    name: str
    description: str
    rows: int
    cols: int
    cells: Tuple[Cell, ...]

    @property
    def n_cells(self) -> int:
        return len(self.cells)

    def resolve_mm(self, width_mm: float, height_mm: float,
                   margin_mm: float = 3.0, gap_mm: float = 2.0) -> List[Rect]:
        """Разложить ячейки в абсолютные (x, y, w, h) в мм.

        margin — внешнее поле фигуры; gap — зазор между соседними ячейками.
        Если после вычитания margin/gap у фигуры не осталось места — вернуть
        пустой список (диалог / apply_template превратят это в осмысленную
        ошибку).
        """
        if self.rows <= 0 or self.cols <= 0:
            return []
        usable_w = width_mm - 2.0 * margin_mm - (self.cols - 1) * gap_mm
        usable_h = height_mm - 2.0 * margin_mm - (self.rows - 1) * gap_mm
        if usable_w <= 0 or usable_h <= 0:
            return []
        cell_w = usable_w / self.cols
        cell_h = usable_h / self.rows
        out: List[Rect] = []
        for (row, col, rowspan, colspan) in self.cells:
            x = margin_mm + col * (cell_w + gap_mm)
            y = margin_mm + row * (cell_h + gap_mm)
            w = colspan * cell_w + (colspan - 1) * gap_mm
            h = rowspan * cell_h + (rowspan - 1) * gap_mm
            out.append((float(x), float(y), float(w), float(h)))
        return out