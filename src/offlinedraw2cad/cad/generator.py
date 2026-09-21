"""Deterministic PartSpec -> build123d generator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..partspec.schema import Chamfer, Fillet, PartSpec, Pocket, Slot, ThroughHole
from ..partspec.validation import validate_partspec
from .features import (
    apply_chamfer,
    apply_fillet,
    cut_pocket,
    cut_slot,
    cut_through_hole,
    make_base,
)


@dataclass
class GenerationResult:
    """Generated solid plus intermediate feature snapshots."""

    shape: Any
    feature_shapes: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def generate_part(spec: PartSpec, *, strict: bool = True) -> GenerationResult:
    """Build a complete deterministic solid from PartSpec.

    Tiers/provenance are deliberately ignored by the CAD layer.
    """
    issues = validate_partspec(spec)
    errors = [i for i in issues if i.severity == "error"]
    if strict and errors:
        raise ValueError(
            "PartSpec cannot be generated:\n" +
            "\n".join(f"{i.path}: {i.message}" for i in errors)
        )

    base = spec.base_feature
    L = base.length.value
    W = base.width.value
    T = base.thickness.value

    shape = make_base(base)
    snapshots: dict[str, Any] = {"base": shape}
    warnings = [f"{i.path}: {i.message}" for i in issues if i.severity == "warning"]

    for feature in spec.features:
        if isinstance(feature, ThroughHole):
            shape = cut_through_hole(
                shape, feature, base_length=L, base_width=W, base_thickness=T
            )
        elif isinstance(feature, Pocket):
            shape = cut_pocket(
                shape, feature, base_length=L, base_width=W, base_thickness=T
            )
        elif isinstance(feature, Slot):
            shape = cut_slot(
                shape, feature, base_length=L, base_width=W, base_thickness=T
            )
        elif isinstance(feature, Fillet):
            shape = apply_fillet(shape, feature, length=L, width=W, thickness=T)
        elif isinstance(feature, Chamfer):
            shape = apply_chamfer(shape, feature, length=L, width=W, thickness=T)
        else:
            raise TypeError(f"Unsupported feature type: {type(feature).__name__}")

        snapshots[feature.id] = shape

    return GenerationResult(shape=shape, feature_shapes=snapshots, warnings=warnings)
