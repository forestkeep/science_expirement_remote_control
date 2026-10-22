"""SessionDataLoader: DataRef → numpy + data-bound аннотации источника."""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SessionDataLoader:
    def __init__(self, session_controller):
        self.session_controller = session_controller

    def resolve(self, panel, data_ref) -> Optional[Dict[str, Any]]:
        if data_ref is None or data_ref.is_empty():
            return None
        sessions = getattr(self.session_controller, "graph_sessions", {}) or {}
        sess = sessions.get(data_ref.session_id)
        if sess is None:
            return None
        gm = getattr(sess, "graph_main", None)
        if gm is None:
            return None
        curve = gm.get_curve(data_ref.series_root_name)
        if curve is None:
            return None
        try:
            xs = curve.filtered_x_data
            ys = curve.filtered_y_data
        except Exception:
            return None
        return {
            "x": xs,
            "y": ys,
            "curve_name": getattr(curve, "curve_name", ""),
            "x_name": getattr(curve.rel_data, "x_current_name", ""),
            "y_name": getattr(curve.rel_data, "y_current_name", ""),
            "saved_style": getattr(curve, "saved_style", None),
            "panel_annotations": self._collect_data_bound(sess, data_ref.series_root_name),
        }

    def _collect_data_bound(self, sess, series_root_name: str) -> List[Dict[str, Any]]:
        ac = getattr(sess, "analysis_controller", None)
        if ac is None:
            return []
        results: List[Dict[str, Any]] = []
        try:
            artifacts = ac.get_artifacts_for_curve(series_root_name)
        except Exception:
            return results
        for art in artifacts:
            payload = getattr(art, "payload", None)
            points = getattr(payload, "points", None) if payload is not None else None
            if not points:
                continue
            for i, pt in enumerate(points):
                x = pt.get("x")
                y = pt.get("y")
                if x is None or y is None:
                    continue
                # Стабильный ID: артефакт + индекс точки в payload.
                aid = f"{art.id}:{i}"
                results.append({
                    "id": aid,
                    "annotation_kind": getattr(art, "tool_id", ""),
                    "x": float(x),
                    "y": float(y),
                    "label": pt.get("label", "") or "",
                })
        return results