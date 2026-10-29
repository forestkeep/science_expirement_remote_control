"""Централизованное управление темой оформления приложения.

Единственное место, где вызывается qdarktheme.setup_theme.
Хранит выбор пользователя в настройках (QSettings) и синхронизирует
os.environ["APP_THEME"] для подсистем, которые читают его напрямую
(схемы установки, менеджер иконок).
"""
from __future__ import annotations

import logging
import os

import qdarktheme
from PyQt5.QtGui import QPalette
from PyQt5.QtWidgets import QApplication

logger = logging.getLogger(__name__)

THEME_DARK = "dark"
THEME_LIGHT = "light"
THEME_AUTO = "auto"

AVAILABLE_THEMES = (THEME_DARK, THEME_LIGHT, THEME_AUTO)

THEME_LABELS = {
    THEME_DARK: "Тёмная",
    THEME_LIGHT: "Светлая",
    THEME_AUTO: "Системная",
}

_CORNER_SHAPE = "sharp"
_SETTINGS_KEY = "theme"

_TOOLTIP_QSS = (
    "QToolTip {"
    " background-color: #1e1e1e;"
    " color: #FFEB3B;"
    " border: 1px solid #4aa3f8;"
    " border-radius: 4px;"
    " padding: 6px 10px;"
    " font-size: 12px;"
    " }"
)


class ThemeManager:
    _instance: "ThemeManager | None" = None

    def __init__(self, settings_manager=None):
        self._settings_manager = settings_manager
        self._current = THEME_DARK
        self._is_dark = True

    @classmethod
    def instance(cls, settings_manager=None) -> "ThemeManager":
        if cls._instance is None:
            cls._instance = cls(settings_manager)
        elif settings_manager is not None and cls._instance._settings_manager is None:
            cls._instance._settings_manager = settings_manager
        return cls._instance

    @property
    def current(self) -> str:
        return self._current

    @property
    def is_dark(self) -> bool:
        return self._is_dark

    @staticmethod
    def available_themes() -> list[str]:
        return list(AVAILABLE_THEMES)

    @staticmethod
    def label(theme: str) -> str:
        return THEME_LABELS.get(theme, theme)

    def _resolve_dark(self, theme: str) -> bool:
        if theme == THEME_DARK:
            return True
        if theme == THEME_LIGHT:
            return False
        return QApplication.palette().color(QPalette.Window).lightness() < 128

    def _apply(self, theme: str) -> None:
        qdarktheme.setup_theme(
            theme,
            corner_shape=_CORNER_SHAPE,
            additional_qss=_TOOLTIP_QSS,
        )
        self._current = theme
        self._is_dark = self._resolve_dark(theme)
        os.environ["APP_THEME"] = THEME_DARK if self._is_dark else THEME_LIGHT

    def initialize(self) -> str:
        """Применить тему из настроек (или default=dark) при старте."""
        theme = THEME_DARK
        if self._settings_manager is not None:
            ok, value = self._settings_manager.get_setting(_SETTINGS_KEY)
            if ok and value in AVAILABLE_THEMES:
                theme = value
        self._apply(theme)
        return theme

    def apply(self, theme: str) -> bool:
        """Применить новую тему и сохранить её в настройках."""
        if theme not in AVAILABLE_THEMES:
            return False
        if theme == self._current:
            return True
        self._apply(theme)
        if self._settings_manager is not None:
            self._settings_manager.save_settings({_SETTINGS_KEY: theme})
        return True