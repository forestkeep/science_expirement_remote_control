from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Callable

import h5py

from .extras import read_attrs, write_attrs
from .hdf5_entities.analysis_artifact import HDF5Artifact
from .hdf5_entities.data_manager import HDF5DataManager
from .hdf5_entities.field_settings import HDF5FieldSettings
from .hdf5_entities.plot import HDF5Plot
from .models import DataManager, SessionUIState
from .schema import SESSION_UI_STATE_SPEC

logger = logging.getLogger(__name__)


@dataclass
class SessionExtension:
    name: str
    save: Callable[[Any, h5py.Group], None]
    load: Callable[[h5py.Group, Any], None]
    order: int = 100


class SessionExtensionRegistry:
    _instance: "SessionExtensionRegistry | None" = None

    def __init__(self) -> None:
        self._extensions: dict[str, SessionExtension] = {}

    @classmethod
    def instance(cls) -> "SessionExtensionRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, name, save, load, order=100) -> None:
        if name in self._extensions:
            logger.warning("session extension %r re-registered", name)
        self._extensions[name] = SessionExtension(name, save, load, order)

    def all_sorted(self) -> list[SessionExtension]:
        return sorted(self._extensions.values(), key=lambda e: (e.order, e.name))

    def save_all(self, session: Any, h5_group: h5py.Group) -> None:
        for ext in self.all_sorted():
            try:
                ext.save(session, h5_group)
            except (OSError, ValueError, TypeError, KeyError) as exc:
                logger.warning("extension %r save failed: %s", ext.name, exc)

    def load_all(self, h5_group: h5py.Group, session: Any) -> None:
        for ext in self.all_sorted():
            try:
                ext.load(h5_group, session)
            except (OSError, ValueError, TypeError, KeyError) as exc:
                logger.warning("extension %r load failed: %s", ext.name, exc)


def register_session_extension(name, save, load, order=100) -> None:
    SessionExtensionRegistry.instance().register(name, save, load, order)


def _save_helpers(session, group):
    if "helpers" in group:
        del group["helpers"]
    hg = group.create_group("helpers")
    for i, h in enumerate(session.helpers or []):
        g = hg.create_group(f"h{i}")
        g.attrs["helper_type"] = h.get("helper_type", "") or ""
        g.attrs["visible"] = bool(h.get("visible", True))
        try:
            g.attrs["params"] = json.dumps(h.get("params", {}), ensure_ascii=False)
        except (TypeError, ValueError):
            g.attrs["params"] = "{}"


def _load_helpers(group, session):
    if "helpers" not in group:
        return
    result = []
    hg = group["helpers"]
    for name in hg:
        g = hg[name]
        ht = g.attrs.get("helper_type", "")
        if isinstance(ht, bytes):
            ht = ht.decode("utf-8", errors="replace")
        if not ht:
            continue
        raw = g.attrs.get("params", "{}")
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        try:
            params = json.loads(raw) if raw else {}
        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning("helpers[%s]: bad params: %s", name, exc)
            params = {}
        result.append({
            "helper_type": ht,
            "params": params,
            "visible": bool(g.attrs.get("visible", True)),
        })
    session.helpers = result


def _save_field_settings(session, group):
    if session.field_settings is None:
        return
    if "field_settings" in group:
        del group["field_settings"]
    HDF5FieldSettings(group.create_group("field_settings")).write(
        session.field_settings
    )


def _load_field_settings(group, session):
    if "field_settings" not in group:
        return
    session.field_settings = HDF5FieldSettings(group["field_settings"]).read()


def _save_data_manager(session, group):
    if "data_manager" in group:
        del group["data_manager"]
    data_manager = session.data_manager or DataManager()
    HDF5DataManager(group.create_group("data_manager")).write(data_manager)


def _load_data_manager(group, session):
    if "data_manager" not in group:
        session.data_manager = DataManager()
        return
    session.data_manager = HDF5DataManager(group["data_manager"]).read()


def _save_plots(session, group):
    if "plots" in group:
        del group["plots"]
    plots_group = group.create_group("plots")
    for name, plot in (session.plots or {}).items():
        HDF5Plot(plots_group.create_group(name)).write(plot)


def _load_plots(group, session):
    if "plots" not in group:
        return
    result = {}
    plots_group = group["plots"]
    for name in plots_group:
        try:
            result[name] = HDF5Plot(plots_group[name]).read()
        except (KeyError, ValueError, TypeError, AttributeError) as exc:
            logger.warning("plot %r load failed: %s", name, exc)
    session.plots = result


def _save_analysis_artifacts(session, group):
    if "analysis_artifacts" in group:
        del group["analysis_artifacts"]
    artifacts_group = group.create_group("analysis_artifacts")
    for artifact in session.analysis_artifacts or []:
        HDF5Artifact(artifacts_group.create_group(artifact.id)).write(artifact)


def _load_analysis_artifacts(group, session):
    if "analysis_artifacts" not in group:
        session.analysis_artifacts = []
        return
    result = []
    artifacts_group = group["analysis_artifacts"]
    for name in artifacts_group:
        try:
            result.append(HDF5Artifact(artifacts_group[name]).read())
        except (KeyError, ValueError, TypeError, OSError) as exc:
            logger.warning("artifact %r load failed: %s", name, exc)
    session.analysis_artifacts = result


def _attr_int(group, name: str, default: int) -> int:
    raw = group.attrs.get(name, default)
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _attr_bool(group, name: str, default: bool) -> bool:
    raw = group.attrs.get(name, default)
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    if isinstance(raw, str):
        return raw.lower() in ("1", "true", "yes", "on")
    return bool(raw)


def _attr_str(group, name: str, default: str) -> str:
    raw = group.attrs.get(name, default)
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace")
    return "" if raw is None else str(raw)


def _attr_json(group, name: str, default):
    raw = group.attrs.get(name, None)
    if raw is None:
        return default
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    if isinstance(raw, str):
        if not raw:
            return default
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return default
    return raw


def _save_ui_state(session, group):
    if "ui_state" in group:
        del group["ui_state"]
    write_attrs(
        group.create_group("ui_state"),
        session.ui_state,
        SESSION_UI_STATE_SPEC,
    )


def _load_ui_state(group, session):
    if "ui_state" in group:
        values, extras = read_attrs(group["ui_state"], SESSION_UI_STATE_SPEC)
        session.ui_state = SessionUIState(**values, extras=extras)
        return

    ui = SessionUIState()
    ui.active_tab = _attr_int(group, "active_tab", 0)
    ui.show_only_active_curves = _attr_bool(
        group, "show_only_active_curves", False
    )
    ui.inspector_current_widget = _attr_str(
        group, "inspector_current_widget", "no_selection"
    )
    ui.inspector_curve_tab = _attr_int(group, "inspector_curve_tab", 0)
    ui.inspector_no_selection_tab = _attr_int(
        group, "inspector_no_selection_tab", 0
    )
    ui.active_analysis_tool = _attr_str(group, "active_analysis_tool", "")
    ui.main_inf_lines = _attr_json(group, "main_inf_lines", [])
    ui.osc_inf_lines = _attr_json(group, "osc_inf_lines", [])
    ui.osc_loop_inf_lines = _attr_json(group, "osc_loop_inf_lines", [])
    ui.applied_preset_name = "—"
    ui.edit_all_axes = True
    session.ui_state = ui


register_session_extension("helpers", _save_helpers, _load_helpers, order=10)
register_session_extension("ui_state", _save_ui_state, _load_ui_state, order=15)
register_session_extension(
    "field_settings", _save_field_settings, _load_field_settings, order=20
)
register_session_extension(
    "data_manager", _save_data_manager, _load_data_manager, order=30
)
register_session_extension("plots", _save_plots, _load_plots, order=40)
register_session_extension(
    "analysis_artifacts",
    _save_analysis_artifacts,
    _load_analysis_artifacts,
    order=50,
)