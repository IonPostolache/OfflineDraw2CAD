"""STEP export helpers."""

from __future__ import annotations

from pathlib import Path

from build123d import export_step

from .generator import GenerationResult


def export_generation(
    generation: GenerationResult,
    output_path: str | Path,
) -> Path:
    """Export the final generated shape as a STEP file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    export_step(generation.shape, str(path))
    return path
