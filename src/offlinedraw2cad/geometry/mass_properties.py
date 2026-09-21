"""Mass/volume properties using OpenCASCADE."""

from __future__ import annotations

from dataclasses import dataclass

from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps


@dataclass(frozen=True)
class MassProperties:
    volume: float
    center_x: float
    center_y: float
    center_z: float


def mass_properties(shape) -> MassProperties:
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, props)
    center = props.CentreOfMass()
    return MassProperties(
        volume=float(props.Mass()),
        center_x=float(center.X()),
        center_y=float(center.Y()),
        center_z=float(center.Z()),
    )


def compare_mass_properties(
    generated: MassProperties,
    reference: MassProperties,
    *,
    relative_volume_tolerance: float = 1e-3,
    absolute_center_tolerance: float = 1e-3,
) -> dict[str, float | bool]:
    volume_scale = max(abs(reference.volume), 1e-12)
    volume_relative_error = abs(generated.volume - reference.volume) / volume_scale
    center_error = (
        (generated.center_x - reference.center_x) ** 2
        + (generated.center_y - reference.center_y) ** 2
        + (generated.center_z - reference.center_z) ** 2
    ) ** 0.5
    return {
        "volume_relative_error": volume_relative_error,
        "center_error": center_error,
        "volume_within_tolerance": volume_relative_error <= relative_volume_tolerance,
        "center_within_tolerance": center_error <= absolute_center_tolerance,
    }
