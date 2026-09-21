import pytest

from offlinedraw2cad.partspec.schema import (
    BaseFeature,
    BaseFeatureType,
    Dimension,
    PartSpec,
    Position2D,
    Provenance,
    ThroughHole,
    Tier,
)


def dim(value, tier=Tier.CONFIRMED):
    return Dimension(
        value=value,
        provenance=Provenance(tier=tier, confidence=1.0),
    )


def pos(x, y, tier=Tier.CONFIRMED):
    return Position2D(
        x=x,
        y=y,
        provenance=Provenance(tier=tier, confidence=1.0),
    )


def test_partspec_accepts_basic_part():
    spec = PartSpec(
        base_feature=BaseFeature(
            type=BaseFeatureType.PLATE,
            length=dim(100),
            width=dim(60),
            thickness=dim(5),
        ),
        features=[
            ThroughHole(
                id="H1",
                diameter=dim(10),
                position=pos(20, 20),
            )
        ],
    )
    assert spec.base_feature.length.value == 100
    assert spec.items_needing_review() == []


def test_assumed_value_is_reviewable():
    spec = PartSpec(
        base_feature=BaseFeature(
            type=BaseFeatureType.PLATE,
            length=dim(100),
            width=dim(60),
            thickness=dim(5),
        ),
        features=[
            ThroughHole(
                id="H1",
                diameter=dim(10, Tier.ASSUMED),
                position=pos(20, 20),
            )
        ],
    )
    items = spec.items_needing_review()
    assert len(items) == 1
    assert items[0][0] == "H1.diameter"


def test_duplicate_feature_ids_are_rejected():
    with pytest.raises(ValueError):
        PartSpec(
            base_feature=BaseFeature(
                type=BaseFeatureType.PLATE,
                length=dim(100),
                width=dim(60),
                thickness=dim(5),
            ),
            features=[
                ThroughHole(id="H1", diameter=dim(10), position=pos(20, 20)),
                ThroughHole(id="H1", diameter=dim(8), position=pos(80, 20)),
            ],
        )
