"""Базовый интерфейс стратегий анализа."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ValidationResult:
    ok: bool = True
    message: str = ""


@dataclass
class AnalysisContext:
    sources: List[Any] = field(default_factory=list)
    filter_instance: Any = None
    alias_manager: Any = None
    cancel_token: Any = None
    progress_callback: Optional[Callable[[int, int], None]] = None


class AnalysisStrategy(ABC):
    supports_incremental: bool = False

    def validate(self, params: Dict[str, Any], sources: List[Any]) -> ValidationResult:
        if not sources:
            return ValidationResult(False, "Не выделено ни одной кривой")
        return ValidationResult(True)

    @abstractmethod
    def compute(self, context: AnalysisContext, params: Dict[str, Any]) -> Any:
        ...

    def describe(self, params: Dict[str, Any]) -> str:
        return ""