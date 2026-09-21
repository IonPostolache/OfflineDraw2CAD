"""A dependency-light HTML review view.

The V1 overlay is intentionally a 2D engineering-style top view generated
from PartSpec. It is not presented as a true CAD renderer. Its purpose is to
make uncertain feature locations and review items immediately visible while
the CAD viewer integration is developed.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

from ..partspec.schema import PartSpec, Pocket, Slot, ThroughHole, Tier

_TIER_CLASS = {
    Tier.CONFIRMED: "confirmed",
    Tier.INFERRED: "inferred",
    Tier.ASSUMED: "assumed",
    Tier.AMBIGUOUS: "ambiguous",
}


def _feature_svg(feature, length: float, width: float, scale: float) -> str:
    cls = _TIER_CLASS.get(
        getattr(feature, "provenance", None).tier
        if hasattr(getattr(feature, "provenance", None), "tier")
        else Tier.CONFIRMED,
        "confirmed",
    )

    if isinstance(feature, ThroughHole):
        x, y = feature.position.x * scale, feature.position.y * scale
        r = feature.diameter.value * scale / 2
        return f'<circle class="{cls}" cx="{x:.2f}" cy="{(width*scale-y):.2f}" r="{r:.2f}"/>'

    if isinstance(feature, (Pocket, Slot)):
        x = feature.position.x * scale
        y = width * scale - feature.position.y * scale
        w = feature.length.value * scale
        h = feature.width.value * scale
        return (
            f'<rect class="{cls}" x="{x-w/2:.2f}" y="{y-h/2:.2f}" '
            f'width="{w:.2f}" height="{h:.2f}" rx="{min(h/2, 8):.2f}"/>'
        )

    return ""


def write_review_html(spec: PartSpec, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    L = spec.base_feature.length.value
    W = spec.base_feature.width.value
    scale = min(800 / max(L, 1), 500 / max(W, 1))

    review = spec.items_needing_review()
    items_html = []
    for label, value in review:
        p = value.provenance
        value_text = getattr(value, "value", "pattern")
        items_html.append(
            f'<div class="item {p.tier.value}">'
            f'<b>{escape(label)}</b>'
            f'<span>Tier: {escape(p.tier.value)} · Confidence: {p.confidence:.0%}</span>'
            f'<span>Value: {escape(str(value_text))}</span>'
            f'<span>{escape(p.reasoning or "")}</span>'
            f'</div>'
        )

    svg_features = "".join(
        _feature_svg(feature, L, W, scale) for feature in spec.features
    )

    html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>OfflineDraw2CAD review</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 24px; background: #f5f5f5; color: #222; }}
.grid {{ display: grid; grid-template-columns: minmax(500px, 1fr) 360px; gap: 24px; }}
.card {{ background: white; padding: 18px; border-radius: 10px; box-shadow: 0 1px 5px #bbb; }}
svg {{ background: white; border: 1px solid #aaa; max-width: 100%; }}
.base {{ fill: #eee; stroke: #222; stroke-width: 2; }}
.confirmed {{ fill: #aaa; stroke: #333; stroke-width: 1.5; }}
.inferred {{ fill: #f1c40f; stroke: #8a6d00; stroke-width: 2; }}
.assumed {{ fill: #e74c3c; stroke: #8e2b22; stroke-width: 2; }}
.ambiguous {{ fill: #f39c12; stroke: #8a4b00; stroke-width: 2; }}
.item {{ padding: 12px; margin: 8px 0; border-left: 6px solid #999; background: #fafafa; }}
.item.assumed {{ border-color: #e74c3c; }}
.item.ambiguous {{ border-color: #f39c12; }}
.item span {{ display: block; margin-top: 4px; color: #555; }}
</style>
</head>
<body>
<h1>OfflineDraw2CAD review</h1>
<div class="grid">
<div class="card">
<h2>Top view</h2>
<svg width="{L*scale:.0f}" height="{W*scale:.0f}" viewBox="0 0 {L*scale:.2f} {W*scale:.2f}">
<rect class="base" x="0" y="0" width="{L*scale:.2f}" height="{W*scale:.2f}"/>
{svg_features}
</svg>
<p>Feature colors indicate provenance tier. This V1 view is a review aid, not a replacement for a CAD viewer.</p>
</div>
<div class="card">
<h2>{len(review)} item(s) need attention</h2>
{''.join(items_html) if items_html else '<p>No assumed or ambiguous values.</p>'}
</div>
</div>
</body>
</html>"""
    path.write_text(html, encoding="utf-8")
    return path
