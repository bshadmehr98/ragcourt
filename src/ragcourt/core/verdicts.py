"""Filling prompts and reading what a model replied: drafts and verdicts (design §6.1, §6.6)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import cast

THINK = re.compile(r"<think>.*?</think>", re.DOTALL)
YES = {"yes", "correct", "true", "valid", "pass"}
NO = {"no", "incorrect", "false", "invalid", "fail"}


def fill(template: str, **values: str) -> str:
    """The template with each ``{{name}}`` replaced by its value."""
    text = template
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def json_object(reply: str) -> dict[str, object] | None:
    """The JSON object in a reply (after reasoning, inside a code fence or after some words), or None."""
    cleaned = THINK.sub("", reply)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        value: object = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(value, dict):
        return None
    return cast(dict[str, object], value)


@dataclass(frozen=True)
class Draft:
    """What the writer returned: a question and a quote it says answers it."""

    question: str
    quote: str


def read_draft(reply: str) -> Draft | None:
    """The question and quote of a writer's reply, or None when the reply lacks them."""
    data = json_object(reply)
    if data is None:
        return None
    question, quote = data.get("question"), data.get("quote")
    if (
        not isinstance(question, str)
        or not isinstance(quote, str)
        or not question.strip()
        or not quote.strip()
    ):
        return None
    return Draft(question.strip(), quote.strip())


@dataclass(frozen=True)
class JudgeReply:
    """A judge's verdict and its reason; ``passed`` is None when the reply could not be read."""

    passed: bool | None
    reason: str


def read_verdict(reply: str) -> JudgeReply:
    """A ``{verdict, reason}`` reply: yes/correct is True, no/incorrect is False, anything else unreadable."""
    data = json_object(reply)
    if data is None:
        return JudgeReply(None, f"not JSON: {reply[:80]!r}")
    verdict = str(data.get("verdict", "")).strip().lower()
    reason = str(data.get("reason", "")).strip() or "no reason given"
    if verdict in YES:
        return JudgeReply(passed=True, reason=reason)
    if verdict in NO:
        return JudgeReply(passed=False, reason=reason)
    return JudgeReply(None, f"verdict {verdict!r} is neither yes nor no")


def is_unknown(answer: str) -> bool:
    """True when a closed-book answer says it does not know."""
    cleaned = THINK.sub("", answer).strip().strip(".").upper()
    return cleaned == "UNKNOWN" or cleaned.startswith("UNKNOWN")
