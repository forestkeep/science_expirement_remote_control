from __future__ import annotations

import h5py

from ..extras import read_attrs, write_attrs
from ..models import FieldSettings
from ..schema import FIELD_SETTINGS_SPEC


class HDF5FieldSettings:
    def __init__(self, group: h5py.Group) -> None:
        self._group = group

    def write(self, settings: FieldSettings) -> None:
        write_attrs(self._group, settings, FIELD_SETTINGS_SPEC)

    def read(self) -> FieldSettings:
        values, extras = read_attrs(self._group, FIELD_SETTINGS_SPEC)
        settings = FieldSettings(**values, extras=extras)

        graph = settings.graph_field
        if not graph.is_multiple_y1_enabled and graph.is_multiple_selection_enabled:
            graph.is_multiple_y1_enabled = True
        if graph.applied_preset_name is None:
            graph.applied_preset_name = "—"
        if graph.edit_all_axes is None:
            graph.edit_all_axes = True

        return settings