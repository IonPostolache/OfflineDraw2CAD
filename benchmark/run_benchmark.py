"""CLI for running a local drawing -> PartSpec -> STEP benchmark."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from metrics import evaluate_case

from offlinedraw2cad.cad import export_generation, generate_part
from offlinedraw2cad.vision.vlm_reader import VLMConfig, VLMReader


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, required=True,
                        help="directory containing case subdirectories")
    parser.add_argument("--output", type=Path, default=Path("benchmark_results.json"))
    parser.add_argument("--model", default="qwen3-vl-30b-a3b-instruct")
    parser.add_argument("--base-url", default="http://localhost:1234/v1")
    args = parser.parse_args()

    reader = VLMReader(VLMConfig(model=args.model, base_url=args.base_url))
    results = []

    for case_dir in sorted(p for p in args.cases.iterdir() if p.is_dir()):
        drawing = next(iter(case_dir.glob("*.png")), None)
        reference = case_dir / "reference.step"
        if drawing is None or not reference.exists():
            continue

        print(f"[{case_dir.name}] reading {drawing.name}")
        spec, warnings = reader.read(drawing)
        generation = generate_part(spec)
        generated_step = case_dir / "generated.step"
        export_generation(generation, generated_step)

        result = evaluate_case(
            case_dir.name,
            generated_step,
            reference,
            spec,
        )
        results.append({
            "case_id": result.case_id,
            "valid_solid": result.valid_solid,
            "iou": result.iou,
            "volume_relative_error": result.volume_relative_error,
            "center_error": result.center_error,
            "tier_counts": result.tier_counts,
            "boolean_error": result.boolean_error,
            "preprocess_warnings": warnings,
            "review_items": len(spec.items_needing_review()),
        })

    # case_objects = []
    # Re-evaluation from serialized results is intentionally avoided: summary
    # uses the same CaseMetrics objects during the main loop in a production
    # harness. The CLI therefore writes a summary from the JSON values below.
    valid = [r for r in results if r["valid_solid"]]
    ious = [r["iou"] for r in valid if r["iou"] is not None]
    tier_totals = {}
    for result in results:
        for key, value in result["tier_counts"].items():
            tier_totals[key] = tier_totals.get(key, 0) + value
    total_values = sum(tier_totals.values())
    no_guess = tier_totals.get("confirmed", 0) + tier_totals.get("inferred", 0)

    summary = {
        "cases": len(results),
        "valid_solids": len(valid),
        "valid_solid_rate": len(valid) / len(results) if results else None,
        "iou_mean_valid": sum(ious) / len(ious) if ious else None,
        "iou_min_valid": min(ious) if ious else None,
        "tier_counts": tier_totals,
        "no_guess_fraction": no_guess / total_values if total_values else None,
    }

    payload = {"summary": summary, "cases": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
