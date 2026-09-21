
import pytest

OCP = pytest.importorskip("OCP")

from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox

from offlinedraw2cad.geometry.checks import validate_shape
from offlinedraw2cad.geometry.iou import volumetric_iou


def test_box_is_valid_and_has_expected_bounds():
    box = BRepPrimAPI_MakeBox(100.0, 50.0, 10.0).Shape()
    result = validate_shape(box)

    assert result.valid
    assert result.solid_count == 1
    assert result.bounding_box.size == pytest.approx((100.0, 50.0, 10.0))


def test_identical_boxes_have_iou_one():
    a = BRepPrimAPI_MakeBox(100.0, 50.0, 10.0).Shape()
    b = BRepPrimAPI_MakeBox(100.0, 50.0, 10.0).Shape()

    result = volumetric_iou(a, b)

    assert result.iou == pytest.approx(1.0, abs=1e-9)
