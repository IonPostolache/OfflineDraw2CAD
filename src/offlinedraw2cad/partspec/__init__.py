"""PartSpec schema and validation."""

from .schema import (
    Alternative,
    BaseFeature,
    BaseFeatureType,
    Chamfer,
    Dimension,
    Feature,
    Fillet,
    PartSpec,
    PatternSpec,
    Pocket,
    Position2D,
    Provenance,
    Slot,
    ThroughHole,
    Tier,
)
from .validation import SanityIssue, validate_partspec

__all__ = [
    "Alternative",
    "BaseFeature",
    "BaseFeatureType",
    "Chamfer",
    "Dimension",
    "Feature",
    "Fillet",
    "PartSpec",
    "PatternSpec",
    "Pocket",
    "Position2D",
    "Provenance",
    "SanityIssue",
    "Slot",
    "ThroughHole",
    "Tier",
    "validate_partspec",
]
