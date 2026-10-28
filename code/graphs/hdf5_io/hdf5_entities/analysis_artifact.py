from __future__ import annotations

from datetime import datetime

import h5py

from graphs.analysis.models import (
    AnalysisArtifact, AnnotationPayload, AttachedPayload, DomainPayload,
    OverlayPayload, PlacementType, UncertaintyPayload,
)
from ..extras import read_attrs, write_attrs
from ..schema import (
    ANALYSIS_ARTIFACT_SPEC, ANNOTATION_PAYLOAD_SPEC, ATTACHED_PAYLOAD_SPEC,
    DOMAIN_PAYLOAD_SPEC, OVERLAY_PAYLOAD_SPEC, UNCERTAINTY_PAYLOAD_SPEC,
)

_PAYLOAD_SPECS = {
    "overlay": (OVERLAY_PAYLOAD_SPEC, OverlayPayload),
    "attached": (ATTACHED_PAYLOAD_SPEC, AttachedPayload),
    "domain": (DOMAIN_PAYLOAD_SPEC, DomainPayload),
    "annotation": (ANNOTATION_PAYLOAD_SPEC, AnnotationPayload),
    "uncertainty": (UNCERTAINTY_PAYLOAD_SPEC, UncertaintyPayload),
}


class HDF5Artifact:
    def __init__(self, group: h5py.Group) -> None:
        self._group = group

    def write(self, artifact: AnalysisArtifact) -> None:
        write_attrs(self._group, artifact, ANALYSIS_ARTIFACT_SPEC)

        if "payload" in self._group:
            del self._group["payload"]

        payload = artifact.payload
        if payload is None:
            return

        payload_group = self._group.create_group("payload")
        kind = getattr(payload, "kind", "overlay")
        payload_group.attrs["kind"] = kind

        spec_info = _PAYLOAD_SPECS.get(kind)
        if spec_info is None:
            return

        write_attrs(payload_group, payload, spec_info[0])

    def read(self) -> AnalysisArtifact:
        values, extras = read_attrs(self._group, ANALYSIS_ARTIFACT_SPEC)

        placement_value = values.get("placement_type", "overlay")
        try:
            placement = PlacementType(placement_value)
        except ValueError:
            placement = PlacementType.OVERLAY

        payload = None
        if "payload" in self._group:
            payload_group = self._group["payload"]
            kind = payload_group.attrs.get("kind", "overlay")
            if isinstance(kind, bytes):
                kind = kind.decode("utf-8", errors="replace")

            spec_info = _PAYLOAD_SPECS.get(kind)
            if spec_info is not None:
                spec, target = spec_info
                payload_values, payload_extras = read_attrs(payload_group, spec)
                payload = target(**payload_values, extras=payload_extras)

        created_at = values.get("created_at")
        if not isinstance(created_at, datetime):
            created_at = datetime.now()

        return AnalysisArtifact(
            id=values.get("id", ""),
            tool_id=values.get("tool_id", ""),
            source_curve_ids=list(values.get("source_curve_ids", [])),
            params=dict(values.get("params", {})),
            placement_type=placement,
            payload=payload,
            visibility=bool(values.get("visibility", True)),
            created_at=created_at,
            order_index=int(values.get("order_index", 0)),
            preset_id=values.get("preset_id"),
            active_uncertainty_id=values.get("active_uncertainty_id"),
            description=values.get("description", ""),
            leader_curve_id=values.get("leader_curve_id"),
            extras=extras,
        )