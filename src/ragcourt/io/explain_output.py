"""``explain``: every held-out miss with its cause, evidence, level and fix (design §9.3)."""

from __future__ import annotations

import textwrap
from typing import Any

from ragcourt.errors import ConfigError
from ragcourt.io.rank_output import causes_text
from ragcourt.io.terminal import legend, section

LEVELS = {
    "confirmed": "a pipeline measured in this run, differing only in the blamed stage, finds the question",
    "indicated": "the probes point to the cause; no alternative was measured (the fix says how to)",
}


def explain_text(results: dict[str, Any], mechanisms: dict[str, str], *, quiet: bool) -> str:
    """Each miss, then the counts, then the legend of every cause used."""
    lines = [f"Run {results['run']}: {results['chosen']}", ""]
    for blame in results["blames"]:
        lines += _miss(blame)
    lines += causes_text(results)
    used = sorted({blame["mechanism"] for blame in results["blames"]})
    if not quiet and used:
        lines += ["", legend({**{name: mechanisms[name] for name in used}, **LEVELS})]
    return "\n".join(lines) + "\n"


def _miss(blame: dict[str, Any]) -> list[str]:
    also = f" (also seen: {', '.join(blame['also_seen'])})" if blame["also_seen"] else ""
    quote = textwrap.shorten(blame["quote"], 160)
    return [
        f"{blame['question']} [{blame['category']}] {blame['text']}",
        f"  quote ({blame['document']}): {quote}",
        f"  cause: {blame['mechanism']}{also}, {blame['level']}",
        f"  evidence: {blame['evidence']}",
        f"  fix: {blame['fix']}",
        "",
    ]


def show_text(results: dict[str, Any], question: str) -> str:
    """One miss with the quote's surroundings and the chunk boundaries marked."""
    for blame in results["blames"]:
        if blame["question"] == question:
            lines = _miss(blame)
            lines += [
                section("Where it is"),
                "« » marks the quote; ⟦n⟧ … ⟧ marks chunk n.",
                "",
                blame["context"],
            ]
            return "\n".join(lines) + "\n"
    raise ConfigError(f"No missed question {question!r} in this run; `ragcourt explain` lists them.")
