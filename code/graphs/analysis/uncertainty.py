"""Оценка погрешностей точек кривой."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict

import numpy as np

DEFAULT_UNCERTAINTY_STYLE = {
    "mode": "bars",       # "bars" | "caps" | "shaded" | "line"
    "color": "auto",      # "auto" | "#rrggbb"
    "width": 1,           # 1..10 px
    "alpha": 180,         # 0..255
    "cap_size": 6,        # 0..40 px
}

def normalize_uncertainty_style(style: dict) -> dict:
    """Привести стиль отображения погрешностей к полному валидному виду."""
    result = dict(DEFAULT_UNCERTAINTY_STYLE)
    if style:
        result.update(style)
    try:
        result["width"] = max(1, min(10, int(result.get("width", 1))))
    except (TypeError, ValueError):
        result["width"] = 1
    try:
        result["alpha"] = max(0, min(255, int(result.get("alpha", 180))))
    except (TypeError, ValueError):
        result["alpha"] = 180
    try:
        result["cap_size"] = max(0, min(40, int(result.get("cap_size", 6))))
    except (TypeError, ValueError):
        result["cap_size"] = 6
    mode = result.get("mode", "bars")
    if mode not in ("bars", "caps", "shaded", "line"):
        mode = "bars"
    result["mode"] = mode
    color = result.get("color", "auto")
    if color is None or color == "":
        color = "auto"
    result["color"] = color
    return result

class UncertaintyMethod:
    STD = "std"
    SEM = "sem"
    CI95 = "ci95"
    BOOTSTRAP = "bootstrap"
    MANUAL = "manual"

    ALL = [STD, SEM, CI95, BOOTSTRAP, MANUAL]


@dataclass
class UncertaintyRecord:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    method: str = UncertaintyMethod.STD
    params: Dict[str, Any] = field(default_factory=dict)
    x_err: Any = None
    y_err: Any = None
    created_at: datetime = field(default_factory=datetime.now)
    visibility: bool = True
    style: Dict[str, Any] = field(default_factory=dict)


def compute_uncertainty(method: str, x: np.ndarray, y: np.ndarray,
                        params: Dict[str, Any]) -> "UncertaintyRecord":
    """Чистая функция. Возвращает UncertaintyRecord без id."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    rec = UncertaintyRecord(method=method, params=dict(params or {}))
    y_err = np.zeros_like(y)

    if method == UncertaintyMethod.STD:
        window = int(params.get("window", 0) or 0)
        if window > 1:
            for i in range(len(y)):
                lo = max(0, i - window // 2)
                hi = min(len(y), i + window // 2 + 1)
                y_err[i] = float(np.nanstd(y[lo:hi]))
        else:
            y_err[:] = float(np.nanstd(y))
    elif method == UncertaintyMethod.SEM:
        window = int(params.get("window", 0) or 0)
        if window > 1:
            for i in range(len(y)):
                lo = max(0, i - window // 2)
                hi = min(len(y), i + window // 2 + 1)
                seg = y[lo:hi]
                n = np.sum(~np.isnan(seg))
                if n > 0:
                    y_err[i] = float(np.nanstd(seg) / np.sqrt(n))
        else:
            n = np.sum(~np.isnan(y))
            y_err[:] = float(np.nanstd(y) / np.sqrt(n)) if n else 0.0
    elif method == UncertaintyMethod.CI95:
        level = float(params.get("level", 0.95) or 0.95)
        z = 1.96 if level == 0.95 else 1.0  # упрощённо
        std = float(np.nanstd(y))
        n = max(1, np.sum(~np.isnan(y)))
        y_err[:] = z * std / np.sqrt(n)
    elif method == UncertaintyMethod.BOOTSTRAP:
        n_iter = int(params.get("iterations", 200) or 200)
        std = float(np.nanstd(y))
        n = max(1, np.sum(~np.isnan(y)))
        boot_stds = []
        rng = np.random.default_rng(0)
        for _ in range(min(n_iter, 500)):
            sample = rng.choice(y[~np.isnan(y)], size=n, replace=True)
            boot_stds.append(np.std(sample))
        y_err[:] = float(np.mean(boot_stds)) if boot_stds else std
    elif method == UncertaintyMethod.MANUAL:
        y_err_val = float(params.get("y_err", 0.0) or 0.0)
        y_err[:] = y_err_val
    else:
        y_err[:] = float(np.nanstd(y))

    rec.y_err = y_err
    rec.x_err = None
    rec.style = normalize_uncertainty_style(rec.style)
    return rec