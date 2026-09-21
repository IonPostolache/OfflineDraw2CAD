"""Volumetric intersection-over-union for two B-rep shapes."""

from __future__ import annotations

from dataclasses import dataclass

from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Fuse
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps


@dataclass(frozen=True)
class IoUResult:
    iou: float | None
    intersection_volume: float | None
    union_volume: float | None
    error: str | None = None


def _volume(shape) -> float:
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, props)
    return float(props.Mass())


def volumetric_iou(generated, reference) -> IoUResult:
    """Compute volume(Common) / volume(Fuse).

    OCC boolean failures are returned as a diagnostic result instead of
    crashing a benchmark run.
    """
    try:
        common = BRepAlgoAPI_Common(generated, reference).Shape()
        fuse = BRepAlgoAPI_Fuse(generated, reference).Shape()

        intersection = _volume(common)
        union = _volume(fuse)

        if union <= 0.0:
            return IoUResult(None, intersection, union, "union volume is zero")

        return IoUResult(intersection / union, intersection, union)
    except Exception as exc: # noqa: BLE001
        return IoUResult(
            None,
            None,
            None,
            f"OCC boolean operation failed: {type(exc).__name__}: {exc}",
        )
