"""Реестр инструментов анализа. Singleton на уровне приложения."""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from .models import AnalysisToolDescriptor, ToolCategory

logger = logging.getLogger(__name__)

class AnalysisToolRegistry:
    _instance: Optional["AnalysisToolRegistry"] = None

    def __init__(self) -> None:
        self._tools: Dict[str, AnalysisToolDescriptor] = {}

    @classmethod
    def instance(cls) -> "AnalysisToolRegistry":
        if cls._instance is None:
            cls._instance = AnalysisToolRegistry()
        return cls._instance

    # ------------------------------------------------------------------
    def register(self, descriptor: AnalysisToolDescriptor) -> None:
        if descriptor.tool_id in self._tools:
            logger.warning("AnalysisToolRegistry: tool %s already registered, overwriting",
                           descriptor.tool_id)
        self._tools[descriptor.tool_id] = descriptor

    def get(self, tool_id: str) -> Optional[AnalysisToolDescriptor]:
        return self._tools.get(tool_id)

    def list_all(self) -> List[AnalysisToolDescriptor]:
        return list(self._tools.values())

    def list_by_category(self, category: ToolCategory) -> List[AnalysisToolDescriptor]:
        return [d for d in self._tools.values() if d.category == category]

    def create_strategy(self, tool_id: str):
        d = self._tools.get(tool_id)
        if d is None or d.strategy_factory is None:
            return None
        return d.strategy_factory()

    def clear(self) -> None:
        self._tools.clear()