"""Reference STEP geometry validation."""

from .checks import (
    BoundingBox,
    ShapeCheckResult,
    load_step,
    validate_shape,
)
from .iou import IoUResult, volumetric_iou
from .mass_properties import MassProperties, compare_mass_properties, mass_properties

__all__ = [
    "BoundingBox",
    "IoUResult",
    "MassProperties",
    "ShapeCheckResult",
    "compare_mass_properties",
    "load_step",
    "mass_properties",
    "validate_shape",
    "volumetric_iou",
]
