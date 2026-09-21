"""Deterministic build123d feature operations.

The functions in this module contain no VLM logic.  They receive concrete
numbers from PartSpec and return CAD geometry.

Coordinate convention:
origin = bottom-left of base footprint
X = length, Y = width, Z = thickness/out of front view
"""

from __future__ import annotations

import math
from typing import Any

from build123d import Box, Cylinder, Pos


def _pattern_positions(
    x: float,
    y: float,
    pattern: Any,
    *,
    base_length: float,
    base_width: float,
) -> list[tuple[float, float]]:
    if pattern is None:
        return [(x, y)]

    count = pattern.count
    spacing = pattern.spacing.value if pattern.spacing is not None else None
    if spacing is None:
        raise ValueError("pattern.spacing is required")

    if pattern.kind == "linear_x":
        return [(x + i * spacing, y) for i in range(count)]

    if pattern.kind == "linear_y":
        return [(x, y + i * spacing) for i in range(count)]

    if pattern.kind == "circular":
        # V1 convention: position is the first instance and the centre of
        # rotation is the centre of the rectangular base footprint.
        cx, cy = base_length / 2.0, base_width / 2.0
        radius = math.hypot(x - cx, y - cy)
        start_angle = math.atan2(y - cy, x - cx)
        step = math.radians(spacing)
        return [
            (
                cx + radius * math.cos(start_angle + i * step),
                cy + radius * math.sin(start_angle + i * step),
            )
            for i in range(count)
        ]

    raise ValueError(f"Unsupported pattern kind: {pattern.kind}")


def make_base(base: Any) -> Any:
    return Box(base.length.value, base.width.value, base.thickness.value)


def cut_through_hole(
    shape: Any,
    feature: Any,
    *,
    base_length: float,
    base_width: float,
    base_thickness: float,
) -> Any:
    positions = _pattern_positions(
        feature.position.x,
        feature.position.y,
        feature.pattern,
        base_length=base_length,
        base_width=base_width,
    )
    radius = feature.diameter.value / 2.0
    result = shape
    for x, y in positions:
        cutter = Pos(x, y, -0.1) * Cylinder(radius, base_thickness + 0.2)
        result = result - cutter
    return result


def cut_pocket(
    shape: Any,
    feature: Any,
    *,
    base_length: float,
    base_width: float,
    base_thickness: float,
) -> Any:
    positions = _pattern_positions(
        feature.position.x,
        feature.position.y,
        feature.pattern,
        base_length=base_length,
        base_width=base_width,
    )
    result = shape
    for x, y in positions:
        cutter = Pos(
            x - feature.length.value / 2.0,
            y - feature.width.value / 2.0,
            base_thickness - feature.depth.value,
        ) * Box(feature.length.value, feature.width.value, feature.depth.value + 0.1)
        result = result - cutter
    return result


def cut_slot(
    shape: Any,
    feature: Any,
    *,
    base_length: float,
    base_width: float,
    base_thickness: float,
) -> Any:
    """Cut a horizontal capsule-like slot.

    V1 interpretation: length is the overall X dimension and width is the
    overall Y dimension. The straight section therefore has length-width.
    """
    positions = _pattern_positions(
        feature.position.x,
        feature.position.y,
        feature.pattern,
        base_length=base_length,
        base_width=base_width,
    )
    result = shape
    width = feature.width.value
    length = feature.length.value
    if length < width:
        raise ValueError(f"{feature.id}: slot length must be >= slot width")

    depth = feature.depth.value
    r = width / 2.0
    straight = length - width

    for x, y in positions:
        z = base_thickness - depth
        middle = Pos(x - straight / 2.0, y - r, z) * Box(straight, width, depth + 0.1)
        left = Pos(x - straight / 2.0, y, z) * Cylinder(r, depth + 0.1)
        right = Pos(x + straight / 2.0, y, z) * Cylinder(r, depth + 0.1)
        result = result - (middle + left + right)
    return result


def _edge_matches(edge: Any, reference: str, *, length: float, width: float, thickness: float) -> bool:
    """Small deterministic selector for common human-readable edge references.

    This intentionally does not pretend that free-text edge references form a
    complete topology reference system. Unsupported descriptions raise later.
    """
    text = reference.lower()
    bb = edge.bounding_box()
    dx = bb.max.X - bb.min.X
    dy = bb.max.Y - bb.min.Y
    dz = bb.max.Z - bb.min.Z

    vertical = dz > max(dx, dy) * 5.0 and dz > 1e-6
    horizontal_x = dx > max(dy, dz) * 5.0
    horizontal_y = dy > max(dx, dz) * 5.0

    if "vertical" in text:
        return vertical

    if "top" in text:
        return abs(bb.min.Z - thickness) < 1e-5 or abs(bb.max.Z - thickness) < 1e-5

    if "bottom" in text:
        return abs(bb.min.Z) < 1e-5 or abs(bb.max.Z) < 1e-5

    if "left" in text:
        return abs(bb.min.X) < 1e-5

    if "right" in text:
        return abs(bb.max.X - length) < 1e-5

    if "front" in text:
        return abs(bb.min.Y) < 1e-5

    if "back" in text:
        return abs(bb.max.Y - width) < 1e-5

    if "outer" in text:
        return vertical or horizontal_x or horizontal_y

    return False


def _select_edges(shape: Any, reference: str, *, length: float, width: float, thickness: float) -> list[Any]:
    edges = [
        edge for edge in shape.edges()
        if _edge_matches(edge, reference, length=length, width=width, thickness=thickness)
    ]
    if not edges:
        raise ValueError(
            f"No deterministic edge selection for reference {reference!r}. "
            "Use a supported description such as 'all outer vertical edges', "
            "'top edge', 'left edge', 'right edge', 'front edge', or 'back edge'."
        )
    return edges


def apply_fillet(shape: Any, feature: Any, *, length: float, width: float, thickness: float) -> Any:
    edges = _select_edges(
        shape,
        feature.edge_reference,
        length=length,
        width=width,
        thickness=thickness,
    )
    return shape.fillet(feature.radius.value, edges)


def apply_chamfer(shape: Any, feature: Any, *, length: float, width: float, thickness: float) -> Any:
    edges = _select_edges(
        shape,
        feature.edge_reference,
        length=length,
        width=width,
        thickness=thickness,
    )
    return shape.chamfer(feature.distance.value, edges)
