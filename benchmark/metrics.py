"""Benchmark aggregation for geometry and PartSpec provenance metrics."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from statistics import mean, median

from offlinedraw2cad.geometry import (
    load_step,
    mass_properties,
    validate_shape,
    volumetric_iou,
)
from offlinedraw2cad.partspec.schema import PartSpec, Tier


@dataclass(frozen=True)
class CaseMetrics:
    case_id: str
    valid_solid: bool
    iou: float | None
    volume_relative_error: float | None
    center_error: float | None
    tier_counts: dict[str, int]
    boolean_error: str | None = None


def evaluate_case(
    case_id: str,
    generated_step,
    reference_step,
    spec: PartSpec,
) -> CaseMetrics:
    generated = load_step(generated_step)
    reference = load_step(reference_step)

    generated_check = validate_shape(generated)
    # reference_check = validate_shape(reference)

    iou_result = volumetric_iou(generated, reference)

    generated_mp = mass_properties(generated)
    reference_mp = mass_properties(reference)
    volume_error = (
        abs(generated_mp.volume - reference_mp.volume)
        / max(abs(reference_mp.volume), 1e-12)
    )
    center_error = (
        (generated_mp.center_x - reference_mp.center_x) ** 2
        + (generated_mp.center_y - reference_mp.center_y) ** 2
        + (generated_mp.center_z - reference_mp.center_z) ** 2
    ) ** 0.5

    tier_counts = {tier.value: 0 for tier in Tier}
    for feature in spec.features:
        for value in feature.__dict__.values():
            if hasattr(value, "provenance"):
                tier_counts[value.provenance.tier.value] += 1

    return CaseMetrics(
        case_id=case_id,
        valid_solid=generated_check.valid and generated_check.solid_count > 0,
        iou=iou_result.iou,
        volume_relative_error=volume_error,
        center_error=center_error,
        tier_counts=tier_counts,
        boolean_error=iou_result.error,
    )


def summarize(cases: Iterable[CaseMetrics]) -> dict:
    cases = list(cases)
    valid = [c for c in cases if c.valid_solid]
    ious = [c.iou for c in valid if c.iou is not None]

    tier_totals = {tier.value: 0 for tier in Tier}
    for case in cases:
        for key, value in case.tier_counts.items():
            tier_totals[key] += value

    no_guess = tier_totals["confirmed"] + tier_totals["inferred"]
    total_values = sum(tier_totals.values())

    return {
        "cases": len(cases),
        "valid_solids": len(valid),
        "valid_solid_rate": len(valid) / len(cases) if cases else None,
        "iou_mean_valid": mean(ious) if ious else None,
        "iou_median_valid": median(ious) if ious else None,
        "iou_min_valid": min(ious) if ious else None,
        "no_guess_fraction": no_guess / total_values if total_values else None,
        "tier_counts": tier_totals,
        "boolean_failures": sum(c.boolean_error is not None for c in cases),
    }
