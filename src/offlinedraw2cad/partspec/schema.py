"""
PartSpec — the structured intermediate representation between the VLM and
the deterministic CAD generator.

Design rules this schema follows (see PLAN.md for the reasoning):

- Every dimension/feature carries a `tier` (see `Tier`) classifying how its
  value was arrived at. This tier is what drives the review panel: only
  ASSUMED and AMBIGUOUS items are shown to the engineer by default.
- The VLM never emits CAD code — only this structured data. The
  deterministic generator (see `offlinedraw2cad.cad.generator`) builds a
  complete model from a PartSpec regardless of which tier a value came
  from; the generator does not need to know or care about tiers.
- One fixed coordinate convention is used everywhere: origin at the
  bottom-left corner of the base feature's bounding box, X right, Y up,
  Z out of the front view (toward the viewer in the "front" orthographic
  view). Every feature's position is expressed in this frame. Deciding
  this once, here, avoids an entire class of bugs from mismatched
  conventions between the generator, validator, and reviewer.
- V1 vocabulary only: a single rectangular plate/block base, plus
  through-holes, fillets, chamfers, rectangular/circular patterns,
  pockets, and slots. See PLAN.md's "Feature vocabulary progression" for
  what's deliberately not here yet (sheet metal, GD&T, multi-body,
  section views).
- Kept intentionally flat: no multi-view dimension-reference constraint
  graph, no per-dimension numeric-confidence micromanagement beyond the
  per-feature `confidence` field below. See PLAN.md's "Cut or deferred"
  section for why.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator

# --------------------------------------------------------------------------
# Tier classification — the spine of the schema
# --------------------------------------------------------------------------


class Tier(str, Enum):
    """
    How a value's presence in this PartSpec was arrived at.

    Decision procedure (see PLAN.md — this is the exact boundary a VLM is
    most likely to blur, so it is written down once here rather than left
    to prompt-time judgment):

    - CONFIRMED: the drawing states this value explicitly (a labeled
      dimension, an explicit callout).
    - INFERRED: the drawing does not state this value directly, but it is
      strongly derivable from geometry or convention that the drawing DOES
      show (e.g. a hole's position is derivable because the drawing shows
      an obviously symmetric pattern and gives the pattern's overall
      spacing).
    - ASSUMED: the drawing gives NO basis for this value at all. The
      generator had to pick something using engineering convention (see
      offlinedraw2cad.cad — default policy for assumed values).
    - AMBIGUOUS: the drawing DOES give a basis for this value, but that
      basis supports more than one plausible reading (e.g. a depth callout
      that could mean "blind, 5mm" or "through"). The generator builds the
      most likely alternative; this tier is always surfaced in the review
      panel regardless of confidence score — ambiguity, not confidence, is
      what triggers review here.

    CONFIRMED and INFERRED are not shown in the review panel by default.
    ASSUMED and AMBIGUOUS always are.
    """

    CONFIRMED = "confirmed"
    INFERRED = "inferred"
    ASSUMED = "assumed"
    AMBIGUOUS = "ambiguous"


class Provenance(BaseModel):
    """
    Why a value has the tier it has. Used only for the review panel and
    for human debugging — the generator does not read this field.
    """

    tier: Tier
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Model's self-reported confidence, 0-1. Used only to help sort "
            "the review list (e.g. show the least-confident items first); "
            "never a hard gate on its own. In particular, AMBIGUOUS items "
            "are always shown regardless of this score — see Tier docs."
        ),
    )
    reasoning: str = Field(
        default="",
        description=(
            "One short, human-readable sentence explaining the tier — "
            "shown to the engineer in the review panel, e.g. 'Drawing "
            "does not specify a radius for this edge; assumed a common "
            "value for this feature size.'"
        ),
    )


class Alternative(BaseModel):
    """One other plausible reading for an AMBIGUOUS value."""

    description: str = Field(
        description="Short human-readable description, e.g. 'through' or "
        "'measured from the opposite edge'."
    )
    value: float | None = Field(
        default=None,
        description="The alternative numeric value, if it has one (a "
        "purely qualitative alternative like 'through' may leave this "
        "unset and rely on `description` alone).",
    )


# --------------------------------------------------------------------------
# Shared building blocks
# --------------------------------------------------------------------------


class Dimension(BaseModel):
    """
    A single toleranced numeric value with its provenance.

    Used wherever a feature needs a plain number (a diameter, a depth, a
    radius) rather than a compound value like a position.
    """

    value: float
    unit: Literal["mm"] = "mm"
    tolerance: float = Field(
        default=0.5,
        ge=0.0,
        description=(
            "± tolerance in the same unit, used as the comparison "
            "threshold when checking this value against a reference "
            "(e.g. in the CAD-VGDrawing benchmark). Defaults to a fixed "
            "general value when the drawing doesn't specify one — this is "
            "NOT a full nominal/measured/limits uncertainty system, "
            "deliberately; see PLAN.md."
        ),
    )
    provenance: Provenance
    alternatives: list[Alternative] = Field(default_factory=list)

    @model_validator(mode="after")
    def _alternatives_only_when_ambiguous(self) -> Dimension:
        if self.alternatives and self.provenance.tier != Tier.AMBIGUOUS:
            raise ValueError(
                "alternatives should only be populated when tier is "
                "AMBIGUOUS — a confirmed/inferred/assumed value has one "
                "answer, not several plausible ones."
            )
        return self


class Position2D(BaseModel):
    """
    A position in the fixed coordinate convention: origin at the
    bottom-left of the base feature's bounding box, X right, Y up.
    Always in millimeters.
    """

    x: float
    y: float
    provenance: Provenance
    alternatives: list[Alternative] = Field(default_factory=list)

    @model_validator(mode="after")
    def _alternatives_only_when_ambiguous(self) -> Position2D:
        if self.alternatives and self.provenance.tier != Tier.AMBIGUOUS:
            raise ValueError(
                "alternatives should only be populated when tier is "
                "AMBIGUOUS."
            )
        return self


# --------------------------------------------------------------------------
# Base feature
# --------------------------------------------------------------------------


class BaseFeatureType(str, Enum):
    PLATE = "plate"
    BLOCK = "block"


class BaseFeature(BaseModel):
    """
    The starting solid every other feature is cut into or added onto.
    V1 supports a single rectangular plate/block only — no cylinders,
    no multi-body bases. Length runs along X, width along Y, thickness
    along Z, consistent with the fixed coordinate convention above.
    """

    type: BaseFeatureType
    length: Dimension  # along X
    width: Dimension  # along Y
    thickness: Dimension  # along Z


# --------------------------------------------------------------------------
# Features
# --------------------------------------------------------------------------


class PatternSpec(BaseModel):
    """
    Describes a repetition of a feature. Kept minimal for V1: a feature
    either has no pattern (a single instance) or one linear/circular
    pattern. No nested/compound patterns in V1.
    """

    kind: Literal["linear_x", "linear_y", "circular"]
    count: int = Field(ge=2)
    spacing: Dimension | None = Field(
        default=None,
        description="Center-to-center spacing (linear patterns) or angular "
        "step in degrees, stored via Dimension.value (circular patterns).",
    )
    provenance: Provenance


class ThroughHole(BaseModel):
    id: str
    type: Literal["through_hole"] = "through_hole"
    diameter: Dimension
    position: Position2D  # position of the first/reference instance
    pattern: PatternSpec | None = None


class Fillet(BaseModel):
    id: str
    type: Literal["fillet"] = "fillet"
    radius: Dimension
    edge_reference: str = Field(
        description="Human-readable description of which edge this "
        "applies to, e.g. 'all outer vertical edges' or 'top edge, "
        "front-left corner'. Free text in V1 — not a formal edge-ID "
        "system; see PLAN.md on why a full multi-view reference graph "
        "is deliberately out of scope for V1."
    )


class Chamfer(BaseModel):
    id: str
    type: Literal["chamfer"] = "chamfer"
    distance: Dimension
    edge_reference: str


class Pocket(BaseModel):
    id: str
    type: Literal["pocket"] = "pocket"
    length: Dimension
    width: Dimension
    depth: Dimension
    position: Position2D
    pattern: PatternSpec | None = None


class Slot(BaseModel):
    id: str
    type: Literal["slot"] = "slot"
    length: Dimension
    width: Dimension
    depth: Dimension
    position: Position2D
    pattern: PatternSpec | None = None


# Feature = Union[ThroughHole, Fillet, Chamfer, Pocket, Slot]
Feature = ThroughHole | Fillet | Chamfer | Pocket | Slot


# --------------------------------------------------------------------------
# Top-level PartSpec
# --------------------------------------------------------------------------


class PartSpec(BaseModel):
    """
    The complete structured representation of one part, as produced by the
    VLM (offlinedraw2cad.vision) and consumed by the deterministic
    generator (offlinedraw2cad.cad). This is the single source of truth
    the rest of the pipeline is built around:

        drawing -> PartSpec -> deterministic CAD
        PartSpec -> review/edit -> deterministic CAD (re-run)
        PartSpec + reference.step -> geometry validation

    A PartSpec is always "complete" in the sense that every feature has a
    concrete value for every field, regardless of tier — an ASSUMED value
    is a real number the generator can build with, not a placeholder. This
    is what makes the finish-and-flag principle possible: the model is
    always fully buildable, and review is about correcting values, not
    filling gaps.
    """

    schema_version: Literal["0.1"] = "0.1"
    units: Literal["mm"] = "mm"
    base_feature: BaseFeature
    features: list[Feature] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_feature_ids(self) -> PartSpec:
        ids = [f.id for f in self.features]
        duplicates = {i for i in ids if ids.count(i) > 1}
        if duplicates:
            raise ValueError(f"duplicate feature id(s): {sorted(duplicates)}")
        return self

    def items_needing_review(self) -> list[tuple[str, Dimension | Position2D]]:
        """
        Every ASSUMED or AMBIGUOUS value in this spec, paired with a
        human-readable label identifying it (e.g. 'H3.diameter').

        This is the one method the review panel (offlinedraw2cad.review)
        should call — CONFIRMED/INFERRED values are deliberately excluded
        here rather than filtered downstream, so there's a single place
        that encodes "what does the engineer need to see."
        """
        review_tiers = {Tier.ASSUMED, Tier.AMBIGUOUS}
        found: list[tuple[str, Dimension | Position2D]] = []

        for dim, label in (
            (self.base_feature.length, "base.length"),
            (self.base_feature.width, "base.width"),
            (self.base_feature.thickness, "base.thickness"),
        ):
            if dim.provenance.tier in review_tiers:
                found.append((label, dim))

        for feature in self.features:
            for field_name, value in feature.__dict__.items():
                if isinstance(value, (Dimension, Position2D)):
                    if value.provenance.tier in review_tiers:
                        found.append((f"{feature.id}.{field_name}", value))
                # elif isinstance(value, PatternSpec):
                #     if value.provenance.tier in review_tiers:
                #         found.append((f"{feature.id}.pattern", value))  # type: ignore[arg-type]

                elif (
                    isinstance(value, PatternSpec)
                    and value.provenance.tier in review_tiers
                ):
                    found.append((f"{feature.id}.pattern", value))  # type: ignore[arg-type]

        return found