"""Prompts for local VLM PartSpec extraction."""

from __future__ import annotations

import json

from ..partspec.schema import PartSpec

SYSTEM_PROMPT = """You are an engineering drawing interpretation system.

Your task is to convert a dimensioned orthographic mechanical drawing into a
complete PartSpec JSON object.

You MUST:
1. Output only JSON matching the supplied Pydantic schema.
2. Never output Python, build123d code, STEP code, or prose outside JSON.
3. Use millimetres.
4. Use the fixed coordinate system: origin at the bottom-left of the base
   footprint, X right, Y up, Z through the front view.
5. Give every required numeric field a concrete value so the CAD generator can
   build a complete provisional model.
6. Tag each value with exactly one tier:
   confirmed: explicitly stated in the drawing;
   inferred: not directly stated but strongly derivable from visible geometry
             or convention that the drawing itself establishes;
   assumed: the drawing gives no basis for the value and an engineering
             convention was required;
   ambiguous: the drawing provides a basis, but two or more plausible readings
               remain.
7. If a value is ambiguous, provide alternatives when useful.
8. Keep reasoning short and factual.

IMPORTANT DISTINCTION:
- ASSUMED = no drawing evidence supports the selected value.
- AMBIGUOUS = drawing evidence exists, but supports multiple plausible values.
Do not use AMBIGUOUS merely because you are uncertain.
Do not use ASSUMED when the value can be derived from a visible dimension,
symmetry, or pattern.

The generator is deterministic and does not inspect your tier/reasoning.
Your job is to interpret the drawing and provide complete structured data.
"""


def build_user_prompt() -> str:
    schema = PartSpec.model_json_schema()
    return (
        "Return a single PartSpec JSON object for the attached engineering "
        "drawing. Start from the simplest supported V1 base and add only "
        "features that are supported by the drawing. Do not invent feature "
        "types outside the schema.\n\n"
        "Pydantic JSON schema:\n"
        + json.dumps(schema, indent=2)
    )
