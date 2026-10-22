"""Issue/Report — транспорт для UI и экспорта."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Issue:
    severity: str                # "error" | "warning" | "hint"
    code: str
    message: str
    panel_id: Optional[str] = None
    element_id: Optional[str] = None

    def to_dict(self):
        return {
            "severity": self.severity, "code": self.code,
            "message": self.message,
            "panel_id": self.panel_id, "element_id": self.element_id,
        }


@dataclass
class Report:
    errors: List[Issue] = field(default_factory=list)
    warnings: List[Issue] = field(default_factory=list)
    hints: List[Issue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors and not self.warnings

    @property
    def all_issues(self) -> List[Issue]:
        return list(self.errors) + list(self.warnings) + list(self.hints)

    def to_dict(self):
        return {
            "errors": [i.to_dict() for i in self.errors],
            "warnings": [i.to_dict() for i in self.warnings],
            "hints": [i.to_dict() for i in self.hints],
        }