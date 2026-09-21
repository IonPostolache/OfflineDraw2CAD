"""Schema and engineering-sanity validation for PartSpec.

This module deliberately separates:
- Pydantic validation: structural correctness.
- sanity checks: plausible dimensions/locations.

Sanity issues are reported rather than silently changing the VLM output.
"""

from __future__ import annotations

from dataclasses import dataclass

from .schema import PartSpec, Pocket, Position2D, Slot, ThroughHole


@dataclass(frozen=True)
class SanityIssue:
    severity: str  # "error" or "warning"
    path: str
    message: str


def _positive(value: float) -> bool:
    return value > 0.0


def _inside_xy(pos: Position2D, length: float, width: float) -> bool:
    return 0.0 <= pos.x <= length and 0.0 <= pos.y <= width


def validate_partspec(spec: PartSpec, *, raise_on_error: bool = False) -> list[SanityIssue]:
    """Return engineering sanity issues without mutating the PartSpec."""
    issues: list[SanityIssue] = []

    dims = {
        "base.length": spec.base_feature.length.value,
        "base.width": spec.base_feature.width.value,
        "base.thickness": spec.base_feature.thickness.value,
    }
    for name, value in dims.items():
        if not _positive(value):
            issues.append(SanityIssue("error", name, "must be greater than zero"))

    L = spec.base_feature.length.value
    W = spec.base_feature.width.value
    T = spec.base_feature.thickness.value

    for feature in spec.features:
        prefix = feature.id

        if isinstance(feature, ThroughHole):
            d = feature.diameter.value
            if d <= 0:
                issues.append(SanityIssue("error", f"{prefix}.diameter", "must be greater than zero"))
            if d >= min(L, W):
                issues.append(SanityIssue("warning", f"{prefix}.diameter",
                                           "hole diameter is unusually large for the base"))
            if not _inside_xy(feature.position, L, W):
                issues.append(SanityIssue("error", f"{prefix}.position",
                                          "hole reference position lies outside the base"))

        elif isinstance(feature, (Pocket, Slot)):
            for field in ("length", "width", "depth"):
                value = getattr(feature, field).value
                if value <= 0:
                    issues.append(SanityIssue("error", f"{prefix}.{field}",
                                              "must be greater than zero"))
            if feature.depth.value > T:
                issues.append(SanityIssue(
                    "error", f"{prefix}.depth",
                    "blind-cut depth cannot exceed base thickness; use a through feature "
                    "or set depth <= base thickness",
                ))
            if not _inside_xy(feature.position, L, W):
                issues.append(SanityIssue("error", f"{prefix}.position",
                                          "feature reference position lies outside the base"))

        elif hasattr(feature, "radius"):
            if feature.radius.value <= 0:
                issues.append(SanityIssue("error", f"{prefix}.radius",
                                          "must be greater than zero"))

        elif hasattr(feature, "distance"):
            if feature.distance.value <= 0:
                issues.append(SanityIssue("error", f"{prefix}.distance",
                                          "must be greater than zero"))

    if raise_on_error:
        errors = [i for i in issues if i.severity == "error"]
        if errors:
            message = "\n".join(f"{i.path}: {i.message}" for i in errors)
            raise ValueError(f"PartSpec sanity validation failed:\n{message}")

    return issues
