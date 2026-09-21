import pytest

build123d = pytest.importorskip("build123d")

from offlinedraw2cad.cad import generate_part
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


def d(value):
    return Dimension(
        value=value,
        provenance=Provenance(tier=Tier.CONFIRMED, confidence=1.0),
    )


def p(x, y):
    return Position2D(
        x=x,
        y=y,
        provenance=Provenance(tier=Tier.CONFIRMED, confidence=1.0),
    )


def test_plate_with_two_holes_generates_solid():
    spec = PartSpec(
        base_feature=BaseFeature(
            type=BaseFeatureType.PLATE,
            length=d(100),
            width=d(60),
            thickness=d(5),
        ),
        features=[
            ThroughHole(id="H1", diameter=d(10), position=p(20, 30)),
            ThroughHole(id="H2", diameter=d(10), position=p(80, 30)),
        ],
    )

    result = generate_part(spec)
    assert result.shape.is_valid
    assert len(result.feature_shapes) == 3
