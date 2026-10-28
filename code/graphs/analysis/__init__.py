"""Публичный API подсистемы анализа."""
from . import strategies  # noqa: F401  — триггерит регистрацию инструментов

from .models import (
    AnalysisArtifact, AnalysisToolDescriptor, ParamDescriptor, ParamType,
    PlacementType, ToolCategory, SourceSnapshot,
    OverlayPayload, AttachedPayload, DomainPayload,
    AnnotationPayload, UncertaintyPayload, tr_analysis,
)
from .registry import AnalysisToolRegistry
from .store import SessionAnalysisStore
from .controller import AnalysisController
from .commands import (
    ApplyAnalysisCommand, RemoveAnalysisCommand, UpdateAnalysisParamsCommand,
    ApplyUncertaintyCommand, RemoveUncertaintyCommand, MacroAnalysisCommand,
)
from .presets import AnalysisPresetStore
from .uncertainty import UncertaintyRecord, UncertaintyMethod

_initialized = False


def ensure_tools_registered() -> None:
    """Гарантирует регистрацию инструментов (идемпотентно)."""
    global _initialized
    if _initialized:
        return
    try:
        from . import strategies as _s  # noqa: F401
    except ImportError as exc:
        import logging
        logging.getLogger(__name__).warning(
            "ensure_tools_registered: strategies import failed: %s", exc
        )
    _initialized = True