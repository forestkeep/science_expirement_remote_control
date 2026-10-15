"""Базовый интерфейс рендерера."""
from __future__ import annotations

from abc import ABC, abstractmethod


class BaseRenderer(ABC):
    @abstractmethod
    def render(self, artifact, is_preview: bool = False):
        ...

    @abstractmethod
    def update(self, handle, payload) -> None:
        ...

    @abstractmethod
    def remove(self, handle) -> None:
        ...

    @abstractmethod
    def set_visible(self, handle, visible: bool) -> None:
        ...