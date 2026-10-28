"""HDF5-файл проекта. Схема-версия + тривиальный цикл по сессиям."""
from __future__ import annotations

from typing import Optional

import h5py

from .base import BaseHDF5Entity
from ..extras import read_attrs, write_attrs
from ..load_strategies.base import BaseLoadStrategy
from ..models import ProjectFile, Session
from ..schema import PROJECT_FILE_SPEC
from .session import HDF5Session


class HDF5File(BaseHDF5Entity):
    def __init__(self, file_path: str, mode: str = "a",
                 load_strategy: Optional[BaseLoadStrategy] = None):
        self.file_path = file_path
        self.mode = mode
        self._h5file = h5py.File(file_path, mode)
        self.load_strategy = load_strategy
        super().__init__(self._h5file)

    def close(self) -> None:
        self._h5file.close()

    def write_file_attributes(self, project_file: ProjectFile) -> None:
        write_attrs(self._h5file, project_file, PROJECT_FILE_SPEC)

    def read_file_attributes(self) -> tuple[dict, dict]:
        return read_attrs(self._h5file, PROJECT_FILE_SPEC)

    def write_session(self, session: Session, session_id: Optional[str] = None) -> None:
        uuid = session.parameters.uuid
        if uuid in self._h5file:
            del self._h5file[uuid]
        group = self._h5file.create_group(uuid)
        HDF5Session(group).write(session)

    def read_session(self, session_name: str) -> Session:
        if session_name not in self._h5file:
            raise KeyError(f"session {session_name!r} not found")
        return HDF5Session(self._h5file[session_name], self.load_strategy).read()

    def write_aliases(self, aliases) -> None:
        if "aliases" in self._h5file:
            del self._h5file["aliases"]
        g = self._h5file.create_group("aliases")
        for k, v in aliases.items():
            g.attrs[k] = v

    def read_aliases(self) -> dict:
        if "aliases" not in self._h5file:
            return {}
        return dict(self._h5file["aliases"].attrs)

    def get_session_uuids(self) -> list:
        return list(self._h5file.keys())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()