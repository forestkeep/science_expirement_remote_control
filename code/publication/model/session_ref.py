"""Snapshot-based DataRef: данные и стиль фиксируются на момент импорта."""
from __future__ import annotations
import copy
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


_QT_STYLE_NAME = {
    "SolidLine": "Solid",
    "DashLine": "Dash",
    "DotLine": "Dot",
    "DashDotLine": "DashDot",
    "DashDotDotLine": "DashDotDot",
}
_NAME_QT_STYLE = {v: k for k, v in _QT_STYLE_NAME.items()}


def _line_style_to_name(style) -> str:
    if style is None:
        return "Solid"
    if isinstance(style, str):
        return style
    try:
        from PyQt5.QtCore import Qt
        mapping = {
            Qt.SolidLine: "Solid",
            Qt.DashLine: "Dash",
            Qt.DotLine: "Dot",
            Qt.DashDotLine: "DashDot",
            Qt.DashDotDotLine: "DashDotDot",
        }
        return mapping.get(style, "Solid")
    except Exception:
        return "Solid"


def _name_to_line_style(name: str):
    try:
        from PyQt5.QtCore import Qt
        mapping = {
            "Solid": Qt.SolidLine,
            "Dash": Qt.DashLine,
            "Dot": Qt.DotLine,
            "DashDot": Qt.DashDotLine,
            "DashDotDot": Qt.DashDotDotLine,
        }
        return mapping.get(name, Qt.SolidLine)
    except Exception:
        return None


def _style_to_dict(style) -> Optional[Dict[str, Any]]:
    if style is None:
        return None
    return {
        "color": str(getattr(style, "color", "#000000")),
        "line_style": _line_style_to_name(getattr(style, "line_style", None)),
        "line_width": float(getattr(style, "line_width", 1.0)),
        "symbol": getattr(style, "symbol", None),
        "symbol_size": float(getattr(style, "symbol_size", 5.0)),
        "symbol_color": str(getattr(style, "symbol_color", "#ffffff")),
        "fill_color": str(getattr(style, "fill_color", "#ffffff")),
        "px_mode": bool(getattr(style, "px_mode", True)),
    }


def _style_from_dict(data: Optional[Dict[str, Any]]):
    if not data:
        return None
    try:
        from graphs.core.curve_presenter import LineStyle
    except Exception:
        logger.warning("LineStyle недоступен, стиль кривой не восстановлен")
        return None
    style = LineStyle(
        color=data.get("color", "#000000"),
        line_style=_name_to_line_style(data.get("line_style", "Solid")),
        line_width=int(data.get("line_width", 1.0)),
        symbol=data.get("symbol"),
        symbol_size=int(data.get("symbol_size", 5.0)),
        symbol_color=data.get("symbol_color", "#ffffff"),
        fill_color=data.get("fill_color", "#ffffff"),
    )
    style.px_mode = bool(data.get("px_mode", True))
    return style


def _uncertainty_record_to_dict(rec) -> Dict[str, Any]:
    return {
        "id": str(rec.id),
        "method": str(getattr(rec, "method", "std")),
        "params": copy.deepcopy(dict(getattr(rec, "params", {}) or {})),
        "x_err": _ndarray_to_list(getattr(rec, "x_err", None)),
        "y_err": _ndarray_to_list(getattr(rec, "y_err", None)),
        "created_at": getattr(rec, "created_at", datetime.now()).isoformat(),
        "visibility": bool(getattr(rec, "visibility", True)),
        "style": dict(getattr(rec, "style", {}) or {}),
    }


def _uncertainty_record_from_dict(data: Dict[str, Any]):
    try:
        from graphs.analysis.uncertainty import UncertaintyRecord
    except Exception:
        return None
    rec = UncertaintyRecord(
        method=str(data.get("method", "std")),
        params=dict(data.get("params") or {}),
        style=dict(data.get("style") or {}),
    )
    rec.id = str(data.get("id", rec.id))
    rec.x_err = _list_to_ndarray(data.get("x_err"))
    rec.y_err = _list_to_ndarray(data.get("y_err"))
    rec.visibility = bool(data.get("visibility", True))
    return rec


def _ndarray_to_list(arr) -> Optional[list]:
    if arr is None:
        return None
    try:
        return np.asarray(arr).tolist()
    except Exception:
        return None


def _list_to_ndarray(data) -> Optional[np.ndarray]:
    if data is None:
        return None
    try:
        return np.asarray(data, dtype=float)
    except Exception:
        return None


# ------------------------------------------------------------------
# DataSnapshot
# ------------------------------------------------------------------

@dataclass
class DataSnapshot:
    x: np.ndarray
    y: np.ndarray
    x_name: str
    y_name: str
    curve_name: str
    data_version: int
    fingerprint: str
    taken_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def take(cls, curve) -> "DataSnapshot":
        store = getattr(curve, "store", None)
        if store is not None:
            xs = np.asarray(store.filtered_x_data, dtype=float).copy()
            ys = np.asarray(store.filtered_y_data, dtype=float).copy()
            version = int(getattr(store, "data_version", 0))
        else:
            xs = np.asarray(getattr(curve, "filtered_x_data", []), dtype=float).copy()
            ys = np.asarray(getattr(curve, "filtered_y_data", []), dtype=float).copy()
            version = int(getattr(curve, "data_version", 0))
        rel = getattr(curve, "rel_data", None)
        x_name = getattr(rel, "x_current_name", "") if rel is not None else ""
        y_name = getattr(rel, "y_current_name", "") if rel is not None else ""
        curve_name = getattr(curve, "curve_name", "") or ""
        fp = cls._compute_fingerprint(xs, ys, version)
        return cls(
            x=xs, y=ys, x_name=x_name, y_name=y_name,
            curve_name=curve_name, data_version=version,
            fingerprint=fp,
        )

    @staticmethod
    def _compute_fingerprint(x, y, version: int) -> str:
        x_arr = np.asarray(x, dtype=float)
        y_arr = np.asarray(y, dtype=float)
        hasher = hashlib.sha256()
        hasher.update(np.ascontiguousarray(x_arr[:10]).tobytes())
        hasher.update(np.ascontiguousarray(y_arr[:10]).tobytes())
        hasher.update(str(len(x_arr)).encode())
        hasher.update(str(len(y_arr)).encode())
        hasher.update(str(int(version)).encode())
        return hasher.hexdigest()[:16]

    def matches(self, curve) -> bool:
        store = getattr(curve, "store", None)
        if store is not None:
            xs = np.asarray(store.filtered_x_data, dtype=float)
            ys = np.asarray(store.filtered_y_data, dtype=float)
            version = int(getattr(store, "data_version", 0))
        else:
            xs = np.asarray(getattr(curve, "filtered_x_data", []), dtype=float)
            ys = np.asarray(getattr(curve, "filtered_y_data", []), dtype=float)
            version = int(getattr(curve, "data_version", 0))
        current = self._compute_fingerprint(xs, ys, version)
        return current == self.fingerprint

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": np.asarray(self.x).tolist(),
            "y": np.asarray(self.y).tolist(),
            "x_name": self.x_name,
            "y_name": self.y_name,
            "curve_name": self.curve_name,
            "data_version": int(self.data_version),
            "fingerprint": self.fingerprint,
            "taken_at": self.taken_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Optional["DataSnapshot"]:
        if not d:
            return None
        try:
            taken = datetime.fromisoformat(d.get("taken_at", ""))
        except Exception:
            taken = datetime.now()
        return cls(
            x=np.asarray(d.get("x", []), dtype=float),
            y=np.asarray(d.get("y", []), dtype=float),
            x_name=str(d.get("x_name", "")),
            y_name=str(d.get("y_name", "")),
            curve_name=str(d.get("curve_name", "")),
            data_version=int(d.get("data_version", 0)),
            fingerprint=str(d.get("fingerprint", "")),
            taken_at=taken,
        )


# ------------------------------------------------------------------
# StyleSnapshot
# ------------------------------------------------------------------

@dataclass
class StyleSnapshot:
    line_style: Any = None
    uncertainty_records: List[Any] = field(default_factory=list)
    artifacts: List[Any] = field(default_factory=list)
    taken_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def take(cls, curve, artifacts_provider: Optional[Callable] = None) -> "StyleSnapshot":
        style = copy.deepcopy(getattr(curve, "saved_style", None))
        store = getattr(curve, "store", None)
        records: List[Any] = []
        if store is not None:
            for rec in getattr(store, "uncertainty_records", []) or []:
                if getattr(rec, "id", None) in getattr(store, "active_uncertainty_ids", set()):
                    records.append(copy.deepcopy(rec))
        artifacts: List[Any] = []
        if artifacts_provider is not None:
            try:
                artifacts = [copy.deepcopy(a) for a in artifacts_provider(curve)]
            except Exception:
                logger.exception("StyleSnapshot.take: artifacts_provider failed")
        return cls(line_style=style, uncertainty_records=records, artifacts=artifacts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "line_style": _style_to_dict(self.line_style),
            "uncertainty_records": [
                _uncertainty_record_to_dict(r) for r in self.uncertainty_records
            ],
            "artifacts": [_artifact_to_dict(a) for a in self.artifacts],
            "taken_at": self.taken_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, d: Optional[Dict[str, Any]]) -> Optional["StyleSnapshot"]:
        if not d:
            return None
        try:
            taken = datetime.fromisoformat(d.get("taken_at", ""))
        except Exception:
            taken = datetime.now()
        records = [
            _uncertainty_record_from_dict(r)
            for r in d.get("uncertainty_records", []) or []
        ]
        records = [r for r in records if r is not None]
        artifacts = [
            _artifact_from_dict(a) for a in d.get("artifacts", []) or []
        ]
        artifacts = [a for a in artifacts if a is not None]
        return cls(
            line_style=_style_from_dict(d.get("line_style")),
            uncertainty_records=records,
            artifacts=artifacts,
            taken_at=taken,
        )


def _artifact_to_dict(art) -> Dict[str, Any]:
    payload = getattr(art, "payload", None)
    payload_dict = None
    if payload is not None:
        kind = getattr(payload, "kind", "overlay")
        payload_dict = {"kind": kind}
        if kind == "annotation":
            payload_dict["points"] = [
                {
                    "x": float(p.get("x", 0.0)),
                    "y": float(p.get("y", 0.0)),
                    "index": int(p.get("index", -1)),
                    "prominence": p.get("prominence"),
                    "width": p.get("width"),
                    "curve": p.get("curve"),
                }
                for p in getattr(payload, "points", []) or []
            ]
            payload_dict["label"] = getattr(payload, "label", "")
        elif kind == "overlay":
            payload_dict["x"] = [np.asarray(v).tolist() for v in getattr(payload, "x", []) or []]
            payload_dict["y"] = [np.asarray(v).tolist() for v in getattr(payload, "y", []) or []]
            payload_dict["style_hint"] = dict(getattr(payload, "style_hint", {}) or {})
        elif kind == "attached":
            payload_dict["x"] = [np.asarray(v).tolist() for v in getattr(payload, "x", []) or []]
            payload_dict["y"] = [np.asarray(v).tolist() for v in getattr(payload, "y", []) or []]
            payload_dict["y_label"] = getattr(payload, "y_label", "")
            payload_dict["panel_title"] = getattr(payload, "panel_title", "")
        elif kind == "domain":
            payload_dict["x"] = [np.asarray(v).tolist() for v in getattr(payload, "x", []) or []]
            payload_dict["y"] = [np.asarray(v).tolist() for v in getattr(payload, "y", []) or []]
            payload_dict["x_label"] = getattr(payload, "x_label", "")
            payload_dict["y_label"] = getattr(payload, "y_label", "")
            payload_dict["tab_title"] = getattr(payload, "tab_title", "")
        elif kind == "uncertainty":
            payload_dict["x_err"] = _ndarray_to_list(getattr(payload, "x_err", None))
            payload_dict["y_err"] = _ndarray_to_list(getattr(payload, "y_err", None))
            payload_dict["method"] = getattr(payload, "method", "")
            payload_dict["params"] = dict(getattr(payload, "params", {}) or {})
    placement = getattr(art, "placement_type", None)
    placement_value = getattr(placement, "value", None) if placement is not None else None
    return {
        "id": str(getattr(art, "id", "")),
        "tool_id": str(getattr(art, "tool_id", "")),
        "source_curve_ids": list(getattr(art, "source_curve_ids", []) or []),
        "params": dict(getattr(art, "params", {}) or {}),
        "placement_type": placement_value or "overlay",
        "visibility": bool(getattr(art, "visibility", True)),
        "description": str(getattr(art, "description", "")),
        "payload": payload_dict,
    }


def _artifact_from_dict(data: Dict[str, Any]):
    try:
        from graphs.analysis.models import (
            AnalysisArtifact, AnnotationPayload, AttachedPayload,
            DomainPayload, OverlayPayload, PlacementType,
            UncertaintyPayload,
        )
    except Exception:
        return None
    payload_dict = data.get("payload") or {}
    kind = payload_dict.get("kind", "overlay")
    payload = None
    if kind == "annotation":
        payload = AnnotationPayload(
            points=list(payload_dict.get("points", []) or []),
            label=str(payload_dict.get("label", "")),
        )
    elif kind == "overlay":
        payload = OverlayPayload(
            x=[np.asarray(v, dtype=float) for v in payload_dict.get("x", []) or []],
            y=[np.asarray(v, dtype=float) for v in payload_dict.get("y", []) or []],
            style_hint=dict(payload_dict.get("style_hint", {}) or {}),
        )
    elif kind == "attached":
        payload = AttachedPayload(
            x=[np.asarray(v, dtype=float) for v in payload_dict.get("x", []) or []],
            y=[np.asarray(v, dtype=float) for v in payload_dict.get("y", []) or []],
            y_label=str(payload_dict.get("y_label", "")),
            panel_title=str(payload_dict.get("panel_title", "")),
        )
    elif kind == "domain":
        payload = DomainPayload(
            x=[np.asarray(v, dtype=float) for v in payload_dict.get("x", []) or []],
            y=[np.asarray(v, dtype=float) for v in payload_dict.get("y", []) or []],
            x_label=str(payload_dict.get("x_label", "")),
            y_label=str(payload_dict.get("y_label", "")),
            tab_title=str(payload_dict.get("tab_title", "")),
        )
    elif kind == "uncertainty":
        payload = UncertaintyPayload(
            x_err=_list_to_ndarray(payload_dict.get("x_err")),
            y_err=_list_to_ndarray(payload_dict.get("y_err")),
            method=str(payload_dict.get("method", "")),
            params=dict(payload_dict.get("params", {}) or {}),
        )
    try:
        placement = PlacementType(data.get("placement_type", "overlay"))
    except Exception:
        placement = PlacementType.OVERLAY
    return AnalysisArtifact(
        id=str(data.get("id", "")),
        tool_id=str(data.get("tool_id", "")),
        source_curve_ids=list(data.get("source_curve_ids", []) or []),
        params=dict(data.get("params", {}) or {}),
        placement_type=placement,
        payload=payload,
        visibility=bool(data.get("visibility", True)),
        description=str(data.get("description", "")),
    )


# ------------------------------------------------------------------
# DataRef
# ------------------------------------------------------------------

@dataclass
class DataRef:
    session_id: str = ""
    series_root_name: str = ""
    refresh_policy: str = "snapshot"
    data: Optional[DataSnapshot] = None
    style: Optional[StyleSnapshot] = None
    stale_data: bool = False
    stale_style: bool = False

    def is_empty(self) -> bool:
        return not self.session_id or not self.series_root_name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "series_root_name": self.series_root_name,
            "refresh_policy": self.refresh_policy,
            "data": self.data.to_dict() if self.data else None,
            "style": self.style.to_dict() if self.style else None,
            # обратная совместимость со старым полем
            "data_ref": {
                "session_id": self.session_id,
                "series_root_name": self.series_root_name,
            },
        }

    @classmethod
    def from_dict(cls, d: Optional[Dict[str, Any]]) -> Optional["DataRef"]:
        if not d:
            return None
        # Совместимость: старый формат {session_id, series_root_name, x_name, y_name}
        has_new = "refresh_policy" in d or "data" in d or "style" in d
        if not has_new:
            return cls(
                session_id=str(d.get("session_id", "")),
                series_root_name=str(d.get("series_root_name", "")),
                refresh_policy="live",
            )
        return cls(
            session_id=str(d.get("session_id", "")),
            series_root_name=str(d.get("series_root_name", "")),
            refresh_policy=str(d.get("refresh_policy", "snapshot")),
            data=DataSnapshot.from_dict(d.get("data")),
            style=StyleSnapshot.from_dict(d.get("style")),
        )