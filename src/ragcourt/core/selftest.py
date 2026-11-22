"""The judge's self-test: labelled cases it must agree with before its verdicts are used (§6.6, D-026)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ragcourt.core.verdicts import fill, read_verdict
from ragcourt.types.questions import CaseResult


def run_selftest(
    cases: list[dict[str, Any]], templates: dict[str, str], judge: Callable[[str], str]
) -> list[CaseResult]:
    """Ask the judge every case with the same prompts it will use on real questions."""
    results: list[CaseResult] = []
    for case in cases:
        check = str(case["check"])
        values = {key: str(case.get(key, "")) for key in ("question", "quote", "answer")}
        reply = read_verdict(judge(fill(templates[f"judge.{check}"], **values)))
        results.append(
            CaseResult(
                check,
                str(case["kind"]),
                values["question"],
                str(case["expected"]),
                reply.passed,
                reply.reason,
            )
        )
    return results
