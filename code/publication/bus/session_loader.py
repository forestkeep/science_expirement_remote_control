"""SessionDataLoader: DataRef → numpy + снапшоты (данные + стиль)."""
from __future__ import annotations
import logging
from typing import Any, Callable, Dict, Optional

import numpy as np

from ..model.session_ref import DataRef, DataSnapshot, StyleSnapshot

logger = logging.getLogger(__name__)


class SessionDataLoader:
    def __init__(self, session_controller, artifacts_provider: Optional[Callable] = None):
        self.session_controller = session_controller
        self._artifacts_provider = artifacts_provider
        self._missing_warned: set = set()

    def _get_sess(self, session_id: str):
        sessions = getattr(self.session_controller, "graph_sessions", {}) or {}
        return sessions.get(session_id)

    def _get_curve(self, session_id: str, series_root_name: str):
        sess = self._get_sess(session_id)
        if sess is None:
            return None, None
        gm = getattr(sess, "graph_main", None)
        if gm is None:
            return sess, None
        curve = gm.get_curve(series_root_name)
        return sess, curve

    def _collect_artifacts(self, sess, curve) -> list:
        if sess is None or curve is None:
            return []
        ac = getattr(sess, "analysis_controller", None)
        if ac is None:
            return []
        try:
            return ac.get_artifacts_for_curve(curve.rel_data.root_name)
        except Exception:
            logger.exception("collect_artifacts failed")
            return []

    def resolve(self, panel, data_ref: Optional[DataRef]) -> Optional[Dict[str, Any]]:
        if data_ref is None or data_ref.is_empty():
            return None

        sess, curve = self._get_curve(data_ref.session_id, data_ref.series_root_name)

        if curve is None:
            key = (data_ref.session_id, data_ref.series_root_name)
            if key not in self._missing_warned:
                self._missing_warned.add(key)
                logger.warning(
                    "SessionDataLoader: источник %s/%s не найден",
                    data_ref.session_id, data_ref.series_root_name,
                )
            data_ref.stale_data = True
            data_ref.stale_style = True
            return {
                "x": np.array([], dtype=float),
                "y": np.array([], dtype=float),
                "x_name": "",
                "y_name": "",
                "curve_name": "(источник не найден)",
                "style": data_ref.style,
                "orphan": True,
            }

        # --- данные по refresh_policy ---
        if data_ref.refresh_policy == "live":
            store = getattr(curve, "store", None)
            if store is not None:
                x = np.asarray(store.filtered_x_data, dtype=float).copy()
                y = np.asarray(store.filtered_y_data, dtype=float).copy()
            else:
                x = np.asarray(curve.filtered_x_data, dtype=float).copy()
                y = np.asarray(curve.filtered_y_data, dtype=float).copy()
            data_ref.stale_data = False
        else:  # snapshot
            if data_ref.data is None:
                data_ref.data = DataSnapshot.take(curve)
                data_ref.stale_data = False
            else:
                data_ref.stale_data = not data_ref.data.matches(curve)
            x = data_ref.data.x
            y = data_ref.data.y

        # --- стиль всегда из снапшота ---
        if data_ref.style is None:
            artifacts = self._collect_artifacts(sess, curve)
            data_ref.style = StyleSnapshot.take(curve, lambda c: artifacts)
            data_ref.stale_style = False
        else:
            live_style = getattr(curve, "saved_style", None)
            snap_style = data_ref.style.line_style
            if live_style is not None and snap_style is not None:
                same = (
                    str(getattr(live_style, "color", "")) == str(getattr(snap_style, "color", ""))
                    and getattr(live_style, "line_style", None) == getattr(snap_style, "line_style", None)
                    and int(getattr(live_style, "line_width", 0)) == int(getattr(snap_style, "line_width", 0))
                )
                data_ref.stale_style = not same
            else:
                data_ref.stale_style = False

        x_name = data_ref.data.x_name if data_ref.data is not None else getattr(curve.rel_data, "x_current_name", "")
        y_name = data_ref.data.y_name if data_ref.data is not None else getattr(curve.rel_data, "y_current_name", "")
        curve_name = data_ref.data.curve_name if data_ref.data is not None else getattr(curve, "curve_name", "")

        return {
            "x": x,
            "y": y,
            "x_name": x_name,
            "y_name": y_name,
            "curve_name": curve_name,
            "style": data_ref.style,
            "stale": bool(data_ref.stale_data or data_ref.stale_style),
            "orphan": False,
        }


__all__ = ["SessionDataLoader"]