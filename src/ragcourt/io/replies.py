"""Cleaning a model's reply before it leaves the client: reasoning blocks removed (design §11.1)."""

from __future__ import annotations

import re

THINK = re.compile(r"<think>.*?</think>", re.DOTALL)


def clean_reply(text: str) -> str:
    """The reply without ``<think>`` blocks or surrounding whitespace."""
    return THINK.sub("", text).strip()
