"""Тонкий фасад над HDF5File. Никакой ручной сериализации."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from .adapters import HDF5ToProjectAdapter, ProjectToHDF5Adapter
from .hdf5_entities.file import HDF5File
from .load_strategies.base import BaseLoadStrategy
from .load_strategies.full_load_strategy import FullLoadStrategy
from .models import ProjectFile

logger = logging.getLogger(__name__)


def _parse_dt(raw) -> datetime:
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, str) and raw:
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            pass
    return datetime.now()


class HDF5Facade:
    def __init__(self, core_to_hdf5_adapter=None, hdf5_to_core_adapter=None,
                 default_load_strategy: Optional[BaseLoadStrategy] = None):
        self.core_to_hdf5 = core_to_hdf5_adapter or ProjectToHDF5Adapter()
        self.hdf5_to_core = hdf5_to_core_adapter or HDF5ToProjectAdapter()
        self.default_load_strategy = default_load_strategy or FullLoadStrategy()

    def save_project(self, core_project, file_path: str) -> None:
        project_file = self.core_to_hdf5.convert_project(core_project)
        with HDF5File(file_path, "a") as h5:
            h5.write_file_attributes(project_file)
            h5.write_aliases(project_file.aliases)
            for session_id, session in project_file.sessions.items():
                h5.write_session(session, session_id=session_id)
            logger.info("project saved: %s", file_path)

    def load_project(self, file_path: str, core_project_class,
                 load_strategy: Optional[BaseLoadStrategy] = None):
        strategy = load_strategy or self.default_load_strategy
        with HDF5File(file_path, "r", strategy) as h5:
            values, extras = h5.read_file_attributes()
            project_file = ProjectFile(
                name=values.get("name", "") or "",
                description=values.get("description", "") or "",
                version_app=values.get("version_app", "undefined") or "undefined",
                creation_date=_parse_dt(values.get("creation_date")),
                schema_version=int(values.get("schema_version", 0) or 0),
                extras=extras,
                session_order=list(values.get("session_order", []) or []),
                active_session_id=values.get("active_session_id", "") or "",
            )
            if project_file.version_app != getattr(core_project_class, "version_app", None):
                logger.warning(
                    "project version %s differs from core %s",
                    project_file.version_app,
                    getattr(core_project_class, "version_app", "?"),
                )
            project_file.aliases = h5.read_aliases()

            existing = set(h5.get_session_uuids())
            existing.discard("aliases")

            # 1) сначала — сессии в порядке сохранения;
            # 2) затем — остальные (старые файлы без session_order).
            session_ids: list[str] = []
            for sid in project_file.session_order:
                if sid in existing and sid not in session_ids:
                    session_ids.append(sid)
            for sid in existing:
                if sid not in session_ids:
                    session_ids.append(sid)

            for session_id in session_ids:
                project_file.sessions[session_id] = h5.read_session(session_id)

            return self.hdf5_to_core.convert(project_file, core_project_class)