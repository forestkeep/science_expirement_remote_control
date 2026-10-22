"""Базовый интерфейс рендерера. Модель, пресеты и валидация не зависят
от Matplotlib: смена рендерера не должна ничего ломать, кроме этого модуля.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional


class RendererAdapter(ABC):
    @abstractmethod
    def create_figure(self, spec) -> Any:
        ...

    @abstractmethod
    def render(
        self,
        figure_handle: Any,
        spec,
        data_resolver: Callable[[Any, Any], Optional[dict]],
        style_resolver: Callable[[str], Any],
        overrides_resolver: Callable[[str], Any],
    ) -> Any:
        ...

    @abstractmethod
    def save(self, figure_handle: Any, path: str, fmt: str, dpi: int = 300) -> None:
        ...

    @abstractmethod
    def get_native_size_px(self, figure_handle: Any, dpi: float) -> tuple:
        ...