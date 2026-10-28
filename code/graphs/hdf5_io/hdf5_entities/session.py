"""Spec-driven HDF5-сущность сессии.

Пишет/читает только `name`, `description`, `parameters` через схему;
всё остальное (field_settings, data_manager, plots, helpers,
analysis_artifacts) — расширения через реестр `extensions.py`.
"""
from __future__ import annotations

from typing import Optional

import h5py

from .base import BaseHDF5Entity
from ..extensions import SessionExtensionRegistry
from ..extras import read_attrs, write_attrs
from ..load_strategies.base import BaseLoadStrategy
from ..models import Session, SessionParameters
from ..schema import SESSION_PARAMETERS_SPEC, SESSION_SPEC


class HDF5Session(BaseHDF5Entity):
    def __init__(self, hdf5_object: h5py.Group,
                 load_strategy: Optional[BaseLoadStrategy] = None):
        super().__init__(hdf5_object)
        self.load_strategy = load_strategy

    def write(self, session: Session) -> None:
        write_attrs(self._hdf5_object, session, SESSION_SPEC)
        if "parameters" in self._hdf5_object:
            del self._hdf5_object["parameters"]
        write_attrs(
            self._hdf5_object.create_group("parameters"),
            session.parameters, SESSION_PARAMETERS_SPEC,
        )
        SessionExtensionRegistry.instance().save_all(session, self._hdf5_object)

    def read(self) -> Session:
        values, extras = read_attrs(self._hdf5_object, SESSION_SPEC)
        session = Session(
            name=values.get("name", "") or "",
            description=values.get("description", "") or "",
            extras=extras,
        )
        if "parameters" in self._hdf5_object:
            p_values, p_extras = read_attrs(
                self._hdf5_object["parameters"], SESSION_PARAMETERS_SPEC)
            session.parameters = SessionParameters(**p_values, extras=p_extras)
        SessionExtensionRegistry.instance().load_all(self._hdf5_object, session)
        return session