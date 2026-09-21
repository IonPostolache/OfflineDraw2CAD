"""OpenAI-compatible local VLM client for LM Studio."""

from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from ..partspec.schema import PartSpec
from .preprocess import preprocess_drawing
from .prompts import SYSTEM_PROMPT, build_user_prompt

load_dotenv()


@dataclass(frozen=True)
class VLMConfig:
    base_url: str
    model: str
    api_key: str
    timeout_seconds: int = 180
    temperature: float = 0.0
    max_tokens: int = 12000

    @classmethod
    def from_env(cls) -> VLMConfig:
        return cls(
            base_url=os.getenv(
                "LLM_BASE_URL",
                "http://localhost:1234/v1",
            ),
            model=os.getenv(
                "LLM_MODEL",
                "qwen3-vl-30b-a3b-instruct",
            ),
            api_key=os.getenv(
                "LLM_API_KEY",
                "lm-studio",
            ),
        )


class VLMReader:
    """Read one engineering drawing using a local OpenAI-compatible VLM."""

    def __init__(self, config: VLMConfig | None = None):
        self.config = config or VLMConfig.from_env()

        self.client = OpenAI(
            base_url=self.config.base_url,
            api_key=self.config.api_key,
            timeout=self.config.timeout_seconds,
        )

    @staticmethod
    def _image_data_url(image_path: str | Path) -> str:
        path = Path(image_path)
        suffix = path.suffix.lower()

        mime = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
        }.get(suffix, "image/png")

        encoded = base64.b64encode(path.read_bytes()).decode("ascii")

        return f"data:{mime};base64,{encoded}"

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any]:
        text = text.strip()

        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")

            if start < 0 or end <= start:
                raise ValueError(
                    "VLM response did not contain a JSON object"
                )

            return json.loads(text[start:end + 1])

    def read(
        self,
        image_path: str | Path,
        *,
        preprocess: bool = True,
    ) -> tuple[PartSpec, list[str]]:
        """Return validated PartSpec and preprocessing warnings."""

        image_path = Path(image_path)
        warnings: list[str] = []

        if preprocess:
            processed = preprocess_drawing(image_path)
            warnings.extend(processed.warnings)

            import cv2

            ok, encoded = cv2.imencode(".png", processed.image)

            if not ok:
                raise ValueError("Could not encode preprocessed drawing")

            image_b64 = base64.b64encode(
                encoded.tobytes()
            ).decode("ascii")

            image_url = f"data:image/png;base64,{image_b64}"

        else:
            image_url = self._image_data_url(image_path)

        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": build_user_prompt(),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url,
                            },
                        },
                    ],
                },
            ],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content

        if not content:
            raise ValueError("VLM returned an empty response")

        data = self._extract_json(content)

        spec = PartSpec.model_validate(data)

        return spec, warnings