"""Реестр расширений сессии: новая фича = новый модуль.

Каждое расширение получает (session_model, h5_group) и делает всё,
что нужно. Фасад и HDF5Session.write/read превращаются в тривиальные
циклы по реестру.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

import h5py

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


# ---------------------------------------------------------------------------
# Built-in extensions
# ---------------------------------------------------------------------------
def _save_helpers(session, group):
    import json
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
    import json
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
    from .utils import settings_to_dict, save_dict_to_hdf5_with_subgroups
    if session.field_settings is None:
        return
    if "field_settings" in group:
        del group["field_settings"]
    fs_group = group.create_group("field_settings")
    gf = session.field_settings.graph_field
    of = session.field_settings.oscilloscope_field
    if gf is not None:
        save_dict_to_hdf5_with_subgroups(
            fs_group.create_group("graph_field"), settings_to_dict(gf))
    if of is not None:
        save_dict_to_hdf5_with_subgroups(
            fs_group.create_group("oscilloscope_field"), settings_to_dict(of))


def _load_field_settings(group, session):
    from .utils import load_dict_from_hdf5_group, dict_to_graph_field_settings
    from .migrations import migrate
    from .models import FieldSettings, OscilloscopeFieldSettings
    if "field_settings" not in group:
        return
    fs_group = group["field_settings"]
    fs = FieldSettings()
    if "graph_field" in fs_group:
        data = load_dict_from_hdf5_group(fs_group["graph_field"])
        data = migrate(data, from_version=0)     # идемпотентно
        fs.graph_field = dict_to_graph_field_settings(data)
    if "oscilloscope_field" in fs_group:
        og = fs_group["oscilloscope_field"]
        of = OscilloscopeFieldSettings()
        for f in ("name", "description", "title", "background_color",
                  "foreground_color", "grid_color", "x_label", "y_label"):
            setattr(of, f, og.attrs.get(f, getattr(of, f, "")))
        for f in ("grid_enabled", "x_log_mode", "y_log_mode",
                  "x_auto_range", "y_auto_range", "legend_enabled",
                  "antialiasing"):
            setattr(of, f, bool(og.attrs.get(f, getattr(of, f, True))))
        for f in ("grid_alpha",):
            try:
                setattr(of, f, float(og.attrs.get(f, getattr(of, f, 0.5))))
            except (TypeError, ValueError):
                pass
        fs.oscilloscope_field = of
    session.field_settings = fs


def _save_data_manager(session, group):
    from .models import DataManager
    from .hdf5_entities.oscillogram_data import HDF5OscillogramData
    if "data_manager" in group:
        del group["data_manager"]
    dm = session.data_manager or DataManager()
    dm_group = group.create_group("data_manager")
    od = dm_group.create_group("oscillogram_data")
    for name, data in dm.oscillogram_data.items():
        if name in od:
            del od[name]
        HDF5OscillogramData(od.create_group(name)).write(data)
    pd_ = dm_group.create_group("parameters_data")
    for name, data in dm.parameter_data.items():
        safe = name.replace("/", "_") if isinstance(name, str) else str(name)
        if safe in pd_:
            del pd_[safe]
        HDF5OscillogramData(pd_.create_group(safe)).write(data)


def _load_data_manager(group, session):
    from .models import DataManager, OscillogramData, ParameterData
    dm = DataManager()
    if "data_manager" not in group:
        session.data_manager = dm
        return
    dmg = group["data_manager"]
    for name in dmg.get("oscillogram_data", {}):
        eg = dmg["oscillogram_data"][name]
        if "data_values" not in eg or "time_values" not in eg:
            continue
        d = OscillogramData()
        d.device = eg.attrs.get("device", "")
        d.channel = eg.attrs.get("channel", "")
        d.parameter = eg.attrs.get("parameter", "")
        d.time_values = eg["time_values"][:]
        d.data_values = eg["data_values"][:]
        dm.oscillogram_data[name] = d
    for name in dmg.get("parameters_data", {}):
        eg = dmg["parameters_data"][name]
        if "data_values" not in eg or "time_values" not in eg:
            continue
        d = ParameterData()
        d.device = eg.attrs.get("device", "")
        d.channel = eg.attrs.get("channel", "")
        d.parameter = eg.attrs.get("parameter", "")
        d.time_values = eg["time_values"][:]
        d.data_values = eg["data_values"][:]
        dm.parameter_data[name] = d
    session.data_manager = dm


def _save_plots(session, group):
    from .hdf5_entities.plot import HDF5Plot
    if "plots" in group:
        del group["plots"]
    pg = group.create_group("plots")
    for name, plot in (session.plots or {}).items():
        if name in pg:
            del pg[name]
        HDF5Plot(pg.create_group(name)).write(plot)


def _load_plots(group, session):
    from .hdf5_entities.plot import HDF5Plot
    if "plots" not in group:
        return
    result = {}
    pg = group["plots"]
    for name in pg:
        try:
            result[name] = HDF5Plot(pg[name]).read()
        except (KeyError, ValueError, TypeError, AttributeError) as exc:
            logger.warning("plot %r load failed: %s", name, exc)
    session.plots = result


def _save_analysis_artifacts(session, group):
    from graphs.analysis.io.serializer import save_artifacts_list
    save_artifacts_list(session.analysis_artifacts or [], group)


def _load_analysis_artifacts(group, session):
    from graphs.analysis.io.serializer import load_artifacts
    session.analysis_artifacts = load_artifacts(group)


register_session_extension("helpers", _save_helpers, _load_helpers, order=10)
register_session_extension("field_settings", _save_field_settings, _load_field_settings, order=20)
register_session_extension("data_manager", _save_data_manager, _load_data_manager, order=30)
register_session_extension("plots", _save_plots, _load_plots, order=40)
register_session_extension("analysis_artifacts", _save_analysis_artifacts, _load_analysis_artifacts, order=50)