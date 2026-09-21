"""Human-readable reconstruction report."""

from __future__ import annotations

from pathlib import Path

from ..partspec.schema import PartSpec


def build_report(spec: PartSpec) -> str:
    review_items = spec.items_needing_review()
    lines = [
        "# OfflineDraw2CAD reconstruction report",
        "",
        f"- Schema version: `{spec.schema_version}`",
        f"- Units: `{spec.units}`",
        f"- Features: `{len(spec.features)}`",
        f"- Items needing review: **{len(review_items)}**",
        "",
        "## Review items",
        "",
    ]

    if not review_items:
        lines.append("No ASSUMED or AMBIGUOUS values were identified.")
    else:
        for label, value in review_items:
            prov = value.provenance
            lines.extend([
                f"### `{label}`",
                f"- Tier: **{prov.tier.value}**",
                f"- Confidence: {prov.confidence:.0%}",
                f"- Value: `{getattr(value, 'value', 'see feature')}`",
                f"- Reasoning: {prov.reasoning or '—'}",
                "",
            ])

    lines.extend(["## All feature provenance", ""])
    for feature in spec.features:
        lines.append(f"- `{feature.id}`: `{feature.type}`")
        for field_name, value in feature.__dict__.items():
            if hasattr(value, "provenance"):
                lines.append(
                    f"  - `{field_name}`: `{value.provenance.tier.value}`, "
                    f"confidence {value.provenance.confidence:.0%}"
                )
    lines.append("")
    return "\n".join(lines)


def write_report(spec: PartSpec, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_report(spec), encoding="utf-8")
    return path
