"""Reading a model's reply: ``<think>`` blocks removed, the JSON object found and parsed (design §11.1)."""

from __future__ import annotations

import json
import re
from typing import Any, cast

THINK = re.compile(r"<think>.*?</think>", re.DOTALL)
FENCE = re.compile(r"^```(?:json)?\s*|\s*```$")


def clean_reply(text: str) -> str:
    """The reply without reasoning blocks or surrounding whitespace."""
    return THINK.sub("", text).strip()


def parse_json_object(text: str) -> dict[str, Any] | None:
    """The JSON object in a reply (also inside a code fence or after some words), or None."""
    cleaned = FENCE.sub("", clean_reply(text))
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        value = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        return None
    return cast(dict[str, Any], value) if isinstance(value, dict) else None
