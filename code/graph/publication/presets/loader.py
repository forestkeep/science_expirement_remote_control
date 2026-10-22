"""Агрегатор загрузки: объединяет builtin + disk + PlotStyle (если есть)."""
from __future__ import annotations
from typing import Any, Dict, List

from .builtin import SAFE_DEFAULTS, STYLE_PROFILE_DEFAULT
from .journal_preset import JournalPresetStore, JournalPreset
from .plotstyle_adapter import PlotStyleAdapter
from .style_profile import load_style_profile, load_lab_profile


def list_journal_presets(store: JournalPresetStore = None) -> List[str]:
    store = store or JournalPresetStore()
    return store.list_ids()


def load_journal_preset(preset_id: str, store: JournalPresetStore = None) -> JournalPreset:
    store = store or JournalPresetStore()
    p = store.load(preset_id)
    if p is None:
        # fallback: safe defaults как пустой пресет
        return JournalPreset(
            id=preset_id, name=preset_id,
            column={"width_mm": 183, "height_mm": 247, "dpi": 300},
            constraints={}, defaults={},
        )
    # Обогатить defaults через PlotStyle, если доступен
    adapter = PlotStyleAdapter()
    if adapter.is_available():
        extra = adapter.load_style(preset_id) or {}
        for k, v in extra.items():
            p.defaults.setdefault(k, v)
    return p


def load_style_profile_auto(path: str = None) -> Dict[str, Any]:
    adapter = PlotStyleAdapter()
    if adapter.is_available():
        ps = adapter.load_style("default") or {}
        merged = dict(STYLE_PROFILE_DEFAULT)
        merged.update(ps)
        return merged
    return load_style_profile(path)


def load_lab_profile_auto(path: str = None) -> Dict[str, Any]:
    return load_lab_profile(path)