from __future__ import annotations

import h5py

from ..extras import read_attrs, write_attrs
from ..models import DataManager
from ..schema import DATA_MANAGER_SPEC


class HDF5DataManager:
    def __init__(self, group: h5py.Group) -> None:
        self._group = group

    def write(self, data_manager: DataManager) -> None:
        write_attrs(self._group, data_manager, DATA_MANAGER_SPEC)

    def read(self) -> DataManager:
        values, extras = read_attrs(self._group, DATA_MANAGER_SPEC)
        return DataManager(**values, extras=extras)