from __future__ import annotations

import h5py

from ..extras import read_attrs, write_attrs
from ..models import OscillogramData, ParameterData
from ..schema import OSCILLOGRAM_DATA_SPEC, PARAMETER_DATA_SPEC


class HDF5OscillogramData:
    def __init__(self, group: h5py.Group) -> None:
        self._group = group

    def write(self, data: OscillogramData) -> None:
        write_attrs(self._group, data, OSCILLOGRAM_DATA_SPEC)

    def read(self) -> OscillogramData:
        values, extras = read_attrs(self._group, OSCILLOGRAM_DATA_SPEC)
        return OscillogramData(**values, extras=extras)


class HDF5ParameterData:
    def __init__(self, group: h5py.Group) -> None:
        self._group = group

    def write(self, data: ParameterData) -> None:
        write_attrs(self._group, data, PARAMETER_DATA_SPEC)

    def read(self) -> ParameterData:
        values, extras = read_attrs(self._group, PARAMETER_DATA_SPEC)
        return ParameterData(**values, extras=extras)