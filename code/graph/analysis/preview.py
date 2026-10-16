"""Менеджер предпросмотра. Живёт только в контроллере, не попадает в store/undo/HDF5."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class AnalysisPreviewManager:
    def __init__(self) -> None:
        self._payload: Any = None
        self._tool_id: Optional[str] = None
        self._params: Dict[str, Any] = {}
        self._sources: List[str] = []
        self._leader: Optional[str] = None

    def set(self, tool_id: str, params: Dict[str, Any],
            payload: Any, sources: List[str], leader: Optional[str]) -> None:
        self._tool_id = tool_id
        self._params = dict(params or {})
        self._payload = payload
        self._sources = list(sources)
        self._leader = leader

    def clear(self) -> None:
        self._payload = None
        self._tool_id = None
        self._params = {}
        self._sources = []
        self._leader = None

    @property
    def payload(self) -> Any:
        return self._payload

    @property
    def tool_id(self) -> Optional[str]:
        return self._tool_id

    @property
    def leader(self) -> Optional[str]:
        return self._leader

    @property
    def active(self) -> bool:
        return self._payload is not None