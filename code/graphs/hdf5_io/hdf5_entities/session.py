"""Spec-driven HDF5-сущность сессии.

Пишет/читает `name`, `description`, `parameters` через схему;
всё остальное (field_settings, data_manager, plots, helpers,
analysis_artifacts, ui_state) — расширения через реестр `extensions.py`.
"""
from __future__ import annotations

from typing import Optional

import h5py

from ..extensions import SessionExtensionRegistry
from ..extras import read_attrs, write_attrs
from ..load_strategies.base import BaseLoadStrategy
from ..models import Session, SessionParameters
from ..schema import SESSION_PARAMETERS_SPEC, SESSION_SPEC


class HDF5Session:
    def __init__(self, group: h5py.Group,
                 load_strategy: Optional[BaseLoadStrategy] = None):
        self._group = group
        self.load_strategy = load_strategy

    def write(self, session: Session) -> None:
        write_attrs(self._group, session, SESSION_SPEC)
        if "parameters" in self._group:
            del self._group["parameters"]
        write_attrs(
            self._group.create_group("parameters"),
            session.parameters, SESSION_PARAMETERS_SPEC,
        )
        SessionExtensionRegistry.instance().save_all(session, self._group)

    def read(self) -> Session:
        values, extras = read_attrs(self._group, SESSION_SPEC)
        session = Session(
            name=values.get("name", "") or "",
            description=values.get("description", "") or "",
            extras=extras,
        )
        if "parameters" in self._group:
            p_values, p_extras = read_attrs(
                self._group["parameters"], SESSION_PARAMETERS_SPEC
            )
            session.parameters = SessionParameters(**p_values, extras=p_extras)
        SessionExtensionRegistry.instance().load_all(self._group, session)
        return session