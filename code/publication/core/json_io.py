# code/publication/core/json_io.py
"""Тонкие обёртки над общим файловым слоем.

FigureSpec сам зарегистрирован как semantic type "figure_spec"
(см. figure_model.py). Здесь — только удобные save_spec/load_spec для
существующих вызовов.
"""
from __future__ import annotations

from file_io import load_file, save_file

from ..model.figure_model import FigureSpec


def save_spec(spec: FigureSpec, path: str) -> None:
    """Сохранить FigureSpec атомарно через общий save_file."""
    save_file(spec, path, format="json")


def load_spec(path: str) -> FigureSpec:
    """Загрузить FigureSpec через общий dispatch."""
    return load_file(path, hint="figure_spec")