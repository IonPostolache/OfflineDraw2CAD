# OfflineDraw2CAD


## Project stopped after noticed other similar projects like https://www.omnieda.com/mech/



**A free, fully local tool that turns a 2D engineering drawing into a
complete, editable 3D CAD model — flagging every assumption it had to make
— plus an honest benchmark of how well current free/local AI models
actually do at this task.**

No cloud APIs. No data leaves your machine. Built for mechanical design
engineers reconstructing legacy or customer-supplied drawings into usable
CAD, and for anyone curious how far open, local models have actually come
on this problem.

## Two goals, one pipeline

1. **A useful tool.** Give it a drawing, get back a finished parametric
   STEP model plus a short, visual list of anything it had to guess.
2. **An honest answer.** How good are today's free, local vision-language
   models at reconstructing real engineering drawings? Measured against
   [CAD-VGDrawing](https://github.com/lllssc/Drawing2CAD), a real dataset
   of 150,000+ engineering drawings with corresponding CAD models.

## The principle

> **Don't interrupt you unless missing information makes reconstruction
> meaningless. Otherwise, make the best engineering assumption, finish the
> model, and let you review and correct the assumptions afterward.**

## How correctness is checked

**One validation method, usable by anyone.** The tool compares the model
it generates against a **reference STEP file** using geometric comparison —
volumetric intersection-over-union (IoU), mass properties, bounding box.

This is deliberate: whether you're running the built-in benchmark against
CAD-VGDrawing, or you have your own drawing and already have a STEP model
you want to check it against, the exact same check runs. There's no
separate validation path specific to any one dataset's internal format —
just "does the generated shape actually match the reference shape."

```
your drawing ──► pipeline ──► generated.step
                                    │
                          (optional) reference.step you supply
                                    │
                                    ▼
                     IoU + mass properties + bounding box
```

If you don't have a reference STEP (the normal case — you're digitizing a
drawing precisely *because* no 3D model exists yet), the tool skips this
check and relies on its review panel instead: every assumption it made is
flagged for you to confirm, since there's no ground truth to check itself
against.

## What review looks like

The model is color-coded by how certain each feature is:

- **Confirmed** (no highlight) — explicit in the drawing
- **Inferred** (yellow) — strongly implied by symmetry or convention
- **Assumed** (red) — the drawing didn't say; a standard engineering
  default was used
- **Ambiguous** (orange) — more than one reading is plausible; flagged
  regardless of confidence

```
2 items need attention

🔴 H3 — Hole diameter
   Estimate: Ø10   Confidence: 58%
   [Accept] [Edit]

🟠 P1 — Pocket depth
   Estimate: 5 mm   Alternative: through
   [Accept] [Edit]
```

Editing a value triggers a deterministic regeneration of the model. Whether
that regeneration can be limited to just the edited feature (versus
rebuilding steps that come after it in the feature tree) is a build123d
implementation detail being worked out, not a guarantee — either way, the
result is a correct model reflecting your correction.

## The benchmark

Using CAD-VGDrawing's drawing/CAD pairs — reconstructed into actual
reference STEP files as a one-time preprocessing step, since the dataset
stores CAD construction sequences rather than finished solids — the
pipeline is run across a sampled few hundred cases and scored with the
**same IoU-based method** described above:

- Overall shape accuracy (IoU) against the real answer
- What fraction of values needed no guess at all versus required one
- Where richer ground-truth parameters happen to be available in this
  dataset: how close the guesses were, broken down by confidence tier
  (this reuses the tool's own review-panel classification — it isn't a
  separate scoring method)
- Raster vs. vector input, since CAD-VGDrawing provides both for the same
  drawings

**Caveat, stated plainly:** CAD-VGDrawing's drawings are machine-generated
from existing CAD models — clean, single-part, no scan artifacts. A
controlled first benchmark, not a stand-in for messy real legacy drawings,
which are tested separately later without a reference model to check
against.

## How it works

```
drawing (raster, or vector for one optional experiment)
       │
       ▼
 Qwen3-VL (local)
       │
       ▼
 PartSpec — every value tagged confirmed / inferred / assumed / ambiguous
       │
       ▼
 build123d generator (deterministic, always produces a complete model)
       │
       ▼
 generated.step
       │
       ├─► reference.step available → IoU / mass-property comparison
       │
       └─► always → colored review overlay + review panel
```

The vision-language model never touches the CAD kernel directly.

## Default policy for assumptions

Standard engineering convention: a common fillet size relative to the
feature it's on, symmetric placement on an otherwise-symmetric pattern, a
standard general-tolerance class (ISO 2768) when none is specified. Refined
against real data where available, not just intuition.

## Tool stack

| Function | Tool |
|---|---|
| Vision-language model | Qwen3-VL-30B-A3B (local, via LM Studio) |
| CAD kernel | [build123d](https://github.com/gumyr/build123d) |
| Geometry validation | OCP — boolean IoU, mass properties, solid checks |
| Ground-truth reconstruction | DeepCAD's pythonocc script (benchmark setup only) |
| Image preprocessing | OpenCV |
| Schema validation | pydantic |
| Review interface | Simple local web page |
| Test data | [CAD-VGDrawing](https://github.com/lllssc/Drawing2CAD) |

No cloud AI API is required or used.

## Using your own drawing and reference model

If you have a drawing and already have a STEP file for the part (e.g.
checking whether an old drawing still matches a current model), point the
tool at both — it runs the identical IoU-based check used in the built-in
benchmark. If you only have a drawing, the tool still produces a complete
model; you just won't get an automatic accuracy score, and the review panel
becomes the main way to check its work.

## Current scope (V1)

- Base: rectangular plate, block
- Features: through-holes, fillets, chamfers, patterns, pockets, slots
- Input: dimensioned orthographic drawings (raster; vector optional) — not
  isometric or photographed, for V1

Not yet supported: sheet metal, GD&T, section views, multi-body assemblies.

## Comparison to existing free/open tools

Several small open-source and research projects exist nearby — text-to-CAD
agents, photo-to-mesh reconstruction, academic image/vector-to-CAD models
(CAD-Coder, Ortho2CAD, Drawing2CAD itself, whose dataset this project
reuses for a fair comparison point). Most are trained-model research
artifacts, or one-shot generators with no path to correct just the
uncertain parts. This project evaluates a general local VLM plus a
deterministic, editable pipeline, built around review-and-correct rather
than one-shot generation, and validated the same way regardless of who's
using it or what dataset the reference model came from.

## Results

_To be filled in once Phase 3 runs. These numbers are all against
CAD-VGDrawing's reference STEPs (a real answer key). Phase 5's real-scan
results have no reference model to check against and are reported
separately, never in this table — a self-consistency check is a different
and weaker claim than a real accuracy number, and mixing them would
misrepresent both._

| Metric | Raster input | Vector input |
|---|---|---|
| Valid solid rate | — | — |
| Mean / median IoU vs. reference (valid solids only) | — | — |
| Confirmed/inferred (no guess needed) | — | — |
| Assumed/ambiguous (guess needed) | — | — |
| Guess accuracy vs. ground truth (tier breakdown) | — | — |

## Limitations

Experimental. Benchmark numbers reflect CAD-VGDrawing's clean,
machine-generated drawings and their reconstructed reference STEPs — real
scanned drawings have no reference model to check against and are
evaluated qualitatively, later. Assumption defaults are a starting point,
refined against data. Not intended for unsupervised use with no human
review.

## Roadmap

See [PLAN.md](PLAN.md): acquire CAD-VGDrawing and materialize reference
STEPs → deterministic generator → IoU-based validation → VLM reading +
first benchmark → visual overlay and review panel → real scans.

## License

MIT (or your preferred open license) for this project's code. CAD-VGDrawing
has its own license terms — check the
[Drawing2CAD repository](https://github.com/lllssc/Drawing2CAD).
