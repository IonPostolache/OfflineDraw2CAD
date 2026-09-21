"""Lightweight OpenCV preprocessing for engineering drawings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass(frozen=True)
class PreprocessedImage:
    image: np.ndarray
    warnings: list[str]
    rotation_degrees: float


def _estimate_skew(gray: np.ndarray) -> float:
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi / 1800, threshold=max(100, gray.shape[1] // 3))
    if lines is None:
        return 0.0

    angles: list[float] = []
    for line in lines[:100]:
        theta = float(line[0][1])
        angle = theta * 180.0 / np.pi - 90.0
        if -15.0 <= angle <= 15.0:
            angles.append(angle)

    if not angles:
        return 0.0
    return float(np.median(angles))


def _rotate(image: np.ndarray, degrees: float) -> np.ndarray:
    if abs(degrees) < 0.05:
        return image
    h, w = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), degrees, 1.0)
    return cv2.warpAffine(
        image,
        matrix,
        (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


def preprocess_drawing(
    path: str | Path,
    *,
    max_dimension: int = 4096,
    deskew: bool = True,
    denoise: bool = True,
) -> PreprocessedImage:
    """Load and apply conservative preprocessing.

    The VLM should still see dimension text and leader lines; this is not an
    aggressive document-cleaning pipeline.
    """
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"Could not read drawing image: {path}")

    warnings: list[str] = []
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    rotation = _estimate_skew(gray) if deskew else 0.0
    if abs(rotation) > 2.0:
        warnings.append(
            f"estimated skew {rotation:.2f}° exceeds the conservative correction limit"
        )
        rotation = 0.0

    if abs(rotation) > 0.05:
        image = _rotate(image, rotation)

    if denoise:
        image = cv2.fastNlMeansDenoisingColored(image, None, 3, 3, 7, 21)

    h, w = image.shape[:2]
    largest = max(h, w)
    if largest > max_dimension:
        scale = max_dimension / largest
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        warnings.append(f"resized image from {w}x{h} to {image.shape[1]}x{image.shape[0]}")

    gray2 = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    if float(np.mean(gray2)) < 35 or float(np.mean(gray2)) > 245:
        warnings.append("unusual image brightness; dimension readability may be affected")

    return PreprocessedImage(image=image, warnings=warnings, rotation_degrees=rotation)
