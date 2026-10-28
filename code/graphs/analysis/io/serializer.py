"""Сериализация артефактов анализа в HDF5-совместимый словарь."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict

import numpy as np

from ..models import AnalysisArtifact, PlacementType

logger = logging.getLogger(__name__)


def artifact_to_dict(artifact: AnalysisArtifact) -> Dict[str, Any]:
    payload = artifact.payload
    d = {
        "id": artifact.id,
        "tool_id": artifact.tool_id,
        "source_curve_ids": list(artifact.source_curve_ids),
        "params": json.dumps(_jsonable(artifact.params)),
        "placement_type": artifact.placement_type.value,
        "visibility": bool(artifact.visibility),
        "order_index": int(artifact.order_index),
        "created_at": artifact.created_at.isoformat(),
        "preset_id": artifact.preset_id or "",
        "active_uncertainty_id": artifact.active_uncertainty_id or "",
        "description": artifact.description,
    }
    arrays: Dict[str, Any] = {}
    if payload is not None:
        for attr in ("x", "y", "x_err", "y_err"):
            v = getattr(payload, attr, None)
            if v is None:
                continue
            arrays[attr] = [_to_ndarray(item) for item in v] if isinstance(v, list) else _to_ndarray(v)
        arrays["kind"] = getattr(payload, "kind", "")
        for attr in ("x_label", "y_label", "tab_title", "panel_title", "label"):
            arrays[attr] = getattr(payload, attr, "")
        if hasattr(payload, "points"):
            arrays["points"] = json.dumps(payload.points)
    return {"attrs": d, "payload": arrays}


def dict_to_artifact(d: Dict[str, Any], payload_arrays: Dict[str, Any]) -> AnalysisArtifact:
    from ..models import OverlayPayload, AttachedPayload, DomainPayload, AnnotationPayload, UncertaintyPayload
    kind = payload_arrays.get("kind", "overlay")
    if kind == "overlay":
        payload = OverlayPayload(
            x=payload_arrays.get("x", []), y=payload_arrays.get("y", []))
    elif kind == "attached":
        payload = AttachedPayload(
            x=payload_arrays.get("x", []), y=payload_arrays.get("y", []),
            y_label=payload_arrays.get("y_label", ""),
            panel_title=payload_arrays.get("panel_title", ""))
    elif kind == "domain":
        payload = DomainPayload(
            x=payload_arrays.get("x", []), y=payload_arrays.get("y", []),
            x_label=payload_arrays.get("x_label", ""),
            y_label=payload_arrays.get("y_label", ""),
            tab_title=payload_arrays.get("tab_title", ""))
    elif kind == "annotation":
        pts = payload_arrays.get("points", "[]")
        try:
            pts = json.loads(pts) if isinstance(pts, str) else pts
        except Exception:
            pts = []
        payload = AnnotationPayload(points=pts,
                                    label=payload_arrays.get("label", ""))
    elif kind == "uncertainty":
        payload = UncertaintyPayload(
            x_err=payload_arrays.get("x_err"), y_err=payload_arrays.get("y_err"))
    else:
        payload = None

    return AnalysisArtifact(
        id=d["id"],
        tool_id=d["tool_id"],
        source_curve_ids=list(d.get("source_curve_ids", [])),
        params=json.loads(d.get("params", "{}")),
        placement_type=PlacementType(d.get("placement_type", "overlay")),
        payload=payload,
        visibility=bool(d.get("visibility", True)),
        order_index=int(d.get("order_index", 0)),
        preset_id=d.get("preset_id") or None,
        active_uncertainty_id=d.get("active_uncertainty_id") or None,
        description=d.get("description", ""),
    )

def _jsonable(obj: Any):
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, (int, float, str, bool)) or obj is None:
        return obj
    return str(obj)


def save_artifacts_list(artifacts, h5_session_group) -> None:
    """Запись артефактов из списка (расширение HDF5Session)."""
    if "analysis_artifacts" in h5_session_group:
        del h5_session_group["analysis_artifacts"]
    group = h5_session_group.create_group("analysis_artifacts")
    for art in artifacts:
        data = artifact_to_dict(art)
        art_group = group.create_group(art.id)
        for k, v in data["attrs"].items():
            art_group.attrs[k] = v
        payload_group = art_group.create_group("payload")
        for k, v in data["payload"].items():
            if k == "kind" or isinstance(v, str):
                payload_group.attrs[k] = v
            elif isinstance(v, list):
                for i, arr in enumerate(v):
                    payload_group.create_dataset(
                        f"{k}_{i}", data=np.asarray(arr), compression="gzip"
                    )
            else:
                try:
                    payload_group.create_dataset(k, data=np.asarray(v), compression="gzip")
                except (TypeError, ValueError) as exc:
                    logger.warning(
                        "save_artifacts_list: cannot store %r: %s", k, exc)
                    payload_group.attrs[k] = str(v)

def save_artifacts(store, h5_session_group) -> None:
    save_artifacts_list(store.all(), h5_session_group)

def load_artifacts(h5_session_group):
    """Возвращает список AnalysisArtifact из HDF5-группы."""
    if "analysis_artifacts" not in h5_session_group:
        return []
    result = []
    group = h5_session_group["analysis_artifacts"]
    for art_name in group:
        art_group = group[art_name]
        d = dict(art_group.attrs)
        payload_arrays: Dict[str, Any] = {}
        if "payload" in art_group:
            pgroup = art_group["payload"]
            for k, v in pgroup.attrs.items():
                payload_arrays[k] = v
            for k in pgroup:
                ds = pgroup[k]
                payload_arrays[k] = ds[:]
        try:
            result.append(dict_to_artifact(d, payload_arrays))
        except (KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
            logger.warning(
                "artifact %s load failed: %s", art_name, exc
            )
    return result

def _to_ndarray(v):
    try:
        return np.asarray(v)
    except (TypeError, ValueError) as exc:
        logger.debug("_to_ndarray: cannot convert %r: %s", type(v), exc)
        return v