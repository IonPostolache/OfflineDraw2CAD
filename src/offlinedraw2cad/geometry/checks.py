"""OCP STEP loading, solid validity, and bounding-box checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPControl import STEPControl_Reader
from OCP.TopAbs import TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer


@dataclass(frozen=True)
class BoundingBox:
    xmin: float
    ymin: float
    zmin: float
    xmax: float
    ymax: float
    zmax: float

    @property
    def size(self) -> tuple[float, float, float]:
        return (
            self.xmax - self.xmin,
            self.ymax - self.ymin,
            self.zmax - self.zmin,
        )

    @property
    def diagonal(self) -> float:
        x, y, z = self.size
        return (x * x + y * y + z * z) ** 0.5


@dataclass(frozen=True)
class ShapeCheckResult:
    valid: bool
    solid_count: int
    bounding_box: BoundingBox
    message: str = ""


def load_step(path: str | Path):
    """Load all STEP roots into one OCP TopoDS shape."""
    reader = STEPControl_Reader()
    status = reader.ReadFile(str(path))
    if status != IFSelect_RetDone:
        raise ValueError(f"Failed to read STEP file: {path}")
    reader.TransferRoots()
    shape = reader.OneShape()
    if shape.IsNull():
        raise ValueError(f"STEP file contains no usable shape: {path}")
    return shape


def bounding_box(shape) -> BoundingBox:
    box = Bnd_Box()
    BRepBndLib.Add_s(shape, box)
    xmin, ymin, zmin, xmax, ymax, zmax = box.Get()
    return BoundingBox(xmin, ymin, zmin, xmax, ymax, zmax)


def solid_count(shape) -> int:
    explorer = TopExp_Explorer(shape, TopAbs_SOLID)
    count = 0
    while explorer.More():
        count += 1
        explorer.Next()
    return count


def validate_shape(shape) -> ShapeCheckResult:
    analyzer = BRepCheck_Analyzer(shape)
    valid = bool(analyzer.IsValid())
    solids = solid_count(shape)
    bb = bounding_box(shape)
    message = "valid" if valid else "BRepCheck_Analyzer reports invalid geometry"
    if solids == 0:
        valid = False
        message = "shape contains no solid"
    return ShapeCheckResult(valid, solids, bb, message)


def compare_bounding_boxes(
    a: BoundingBox,
    b: BoundingBox,
    *,
    relative_tolerance: float = 1e-3,
) -> bool:
    scale = max(a.diagonal, b.diagonal, 1.0)
    values = (
        abs(a.xmin - b.xmin),
        abs(a.ymin - b.ymin),
        abs(a.zmin - b.zmin),
        abs(a.xmax - b.xmax),
        abs(a.ymax - b.ymax),
        abs(a.zmax - b.zmax),
    )
    return max(values) <= relative_tolerance * scale
