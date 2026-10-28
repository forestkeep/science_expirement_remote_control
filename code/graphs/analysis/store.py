"""Хранилище артефактов анализа в рамках одной сессии."""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from .models import AnalysisArtifact

logger = logging.getLogger(__name__)

class SessionAnalysisStore:
    def __init__(self) -> None:
        self._artifacts: Dict[str, AnalysisArtifact] = {}
        self._order: List[str] = []

    def add(self, artifact: AnalysisArtifact) -> None:
        if artifact.id not in self._artifacts:
            self._order.append(artifact.id)
        artifact.order_index = self._order.index(artifact.id)
        self._artifacts[artifact.id] = artifact

    def remove(self, artifact_id: str) -> Optional[AnalysisArtifact]:
        a = self._artifacts.pop(artifact_id, None)
        if a is not None and artifact_id in self._order:
            self._order.remove(artifact_id)
        return a

    def get(self, artifact_id: str) -> Optional[AnalysisArtifact]:
        return self._artifacts.get(artifact_id)

    def all(self) -> List[AnalysisArtifact]:
        return [self._artifacts[i] for i in self._order if i in self._artifacts]

    def for_curve(self, root_name: str) -> List[AnalysisArtifact]:
        return [a for a in self.all() if root_name in a.source_curve_ids]
