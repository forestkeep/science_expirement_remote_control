"""Загрузка/хранение style profile и lab profile.

Слой `style_profile` — базовый стиль лаборатории/проекта.
Слой `lab_profile` — опциональный более высокий уровень.
"""
from __future__ import annotations
import json
import logging
import os
from typing import Any, Dict

from .builtin import STYLE_PROFILE_DEFAULT

logger = logging.getLogger(__name__)


def load_style_profile(path: str = None) -> Dict[str, Any]:
    if not path or not os.path.exists(path):
        return dict(STYLE_PROFILE_DEFAULT)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return dict(json.load(f))
    except Exception:
        logger.exception("load_style_profile(%r) failed", path)
        return dict(STYLE_PROFILE_DEFAULT)


def load_lab_profile(path: str = None) -> Dict[str, Any]:
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return dict(json.load(f))
    except Exception:
        logger.exception("load_lab_profile(%r) failed", path)
        return {}