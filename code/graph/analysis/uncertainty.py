"""Оценка погрешностей точек кривой."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

import numpy as np


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
    return rec