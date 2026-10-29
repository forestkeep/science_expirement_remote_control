"""Встроенные шаблоны раскладки панелей."""
from __future__ import annotations
from typing import Optional

from .template import LayoutTemplate


BUILTIN_TEMPLATES = (
    LayoutTemplate(
        id="single",
        name="1 × 1",
        description="Одна панель во всю ширину",
        rows=1, cols=1,
        cells=((0, 0, 1, 1),),
    ),
    LayoutTemplate(
        id="row_2",
        name="1 × 2",
        description="Две панели в ряд",
        rows=1, cols=2,
        cells=((0, 0, 1, 1), (0, 1, 1, 1)),
    ),
    LayoutTemplate(
        id="col_2",
        name="2 × 1",
        description="Две панели в столбец",
        rows=2, cols=1,
        cells=((0, 0, 1, 1), (1, 0, 1, 1)),
    ),
    LayoutTemplate(
        id="row_3",
        name="1 × 3",
        description="Три панели в ряд",
        rows=1, cols=3,
        cells=((0, 0, 1, 1), (0, 1, 1, 1), (0, 2, 1, 1)),
    ),
    LayoutTemplate(
        id="col_3",
        name="3 × 1",
        description="Три панели в столбец",
        rows=3, cols=1,
        cells=((0, 0, 1, 1), (1, 0, 1, 1), (2, 0, 1, 1)),
    ),
    LayoutTemplate(
        id="grid_2x2",
        name="2 × 2",
        description="Сетка 2 × 2",
        rows=2, cols=2,
        cells=(
            (0, 0, 1, 1), (0, 1, 1, 1),
            (1, 0, 1, 1), (1, 1, 1, 1),
        ),
    ),
    LayoutTemplate(
        id="grid_2x3",
        name="2 × 3",
        description="Сетка: 2 строки × 3 столбца",
        rows=2, cols=3,
        cells=(
            (0, 0, 1, 1), (0, 1, 1, 1), (0, 2, 1, 1),
            (1, 0, 1, 1), (1, 1, 1, 1), (1, 2, 1, 1),
        ),
    ),
    LayoutTemplate(
        id="grid_3x2",
        name="3 × 2",
        description="Сетка: 3 строки × 2 столбца",
        rows=3, cols=2,
        cells=(
            (0, 0, 1, 1), (0, 1, 1, 1),
            (1, 0, 1, 1), (1, 1, 1, 1),
            (2, 0, 1, 1), (2, 1, 1, 1),
        ),
    ),
    LayoutTemplate(
        id="grid_3x3",
        name="3 × 3",
        description="Сетка 3 × 3",
        rows=3, cols=3,
        cells=tuple((r, c, 1, 1) for r in range(3) for c in range(3)),
    ),
    LayoutTemplate(
        id="big_left",
        name="1 + 2",
        description="Большая панель слева, две малые справа",
        rows=2, cols=3,
        cells=(
            (0, 0, 2, 2),
            (0, 2, 1, 1),
            (1, 2, 1, 1),
        ),
    ),
    LayoutTemplate(
        id="big_right",
        name="2 + 1",
        description="Две малые слева, большая панель справа",
        rows=2, cols=3,
        cells=(
            (0, 0, 1, 1),
            (1, 0, 1, 1),
            (0, 1, 2, 2),
        ),
    ),
    LayoutTemplate(
        id="big_top",
        name="1 сверху / 2 снизу",
        description="Большая панель сверху, две малые снизу",
        rows=2, cols=2,
        cells=(
            (0, 0, 1, 2),
            (1, 0, 1, 1),
            (1, 1, 1, 1),
        ),
    ),
    LayoutTemplate(
        id="big_bottom",
        name="2 сверху / 1 снизу",
        description="Две малые сверху, большая панель снизу",
        rows=2, cols=2,
        cells=(
            (0, 0, 1, 1),
            (0, 1, 1, 1),
            (1, 0, 1, 2),
        ),
    ),
)


def find_template(template_id: str) -> Optional[LayoutTemplate]:
    for t in BUILTIN_TEMPLATES:
        if t.id == template_id:
            return t
    return None