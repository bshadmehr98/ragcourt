"""What ragcourt tells the user before and while models work, in plain words (design §6.6, D-030).

Nothing happens blindly: before any model call the user sees each role, its model, where that choice came
from and what the model is shown; before the first judge call, what the judge is asked and shown and what it
never decides; the self-test case by case; and the drops by reason.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

from ragcourt.io.terminal import section, table
from ragcourt.types.config import Role
from ragcourt.types.questions import SelfTest

WIDTH = 100
ROLE_JOBS = {
    "writer": (
        "writes questions and copies a quote that answers each",
        "one passage of your documents at a time",
    ),
    "judge": (
        "checks questions: valid, of their category, not answerable from memory",
        "a question, its quote, an answer",
    ),
    "embedders": (
        "turn chunks and questions into vectors; ranked against each other",
        "your chunks and questions",
    ),
    "reranker": ("orders the top candidates for a question (the llm reranker)", "a question and 20 chunks"),
    "doctor": ("describes your documents and suggests (or writes) a chunker", "samples of your documents"),
}


def source_words(role: Role) -> str:
    """Where a role's model came from, in words."""
    if role.source == "default":
        return "built-in default"
    if role.source == "flag":
        return "command-line flag"
    path = Path(role.source)
    return str(path.relative_to(Path.cwd())) if path.is_relative_to(Path.cwd()) else role.source


def roles_text(roles: list[Role]) -> str:
    """A table of the roles a step uses: model, where the choice came from, job, what it is shown."""
    rows = [[role.name, ", ".join(role.models), source_words(role), *ROLE_JOBS[role.name]] for role in roles]
    lines = [section("Models"), table(["role", "model", "chosen by", "does", "is shown"], rows)]
    lines.append(
        "Change one with `ragcourt models set ROLE MODEL`, or for one run with a flag (--judge MODEL)."
    )
    return "\n".join(lines)


def judge_text(judge: Role, prompt_hashes: dict[str, str], replaced: list[str]) -> str:
    """The paragraph printed before the first judge call of a run."""
    named = ", ".join(f"{name} ({digest})" for name, digest in sorted(prompt_hashes.items()))
    sentences = [
        f"{', '.join(judge.models)} ({source_words(judge)}) judges the questions before any of them is used.",
        "It is asked: (1) is this a real question, and does the quote answer it on its own?",
        "(2) given an answer the writer wrote WITHOUT your documents, does it state the quote's fact?",
        "If it does, the question is too easy (answerable from memory) and is dropped.",
        "For negation, distractor and numeric questions it also checks the category.",
        "It is shown only the question, the quote, that answer and, for a distractor, the other passage.",
        "It never sees chunks or scores, never decides blame and never computes a metric.",
        f"Prompts: {named}; read them with `ragcourt prompts show NAME`.",
    ]
    if replaced:
        sentences.append(f"Replaced by you: {', '.join(replaced)}; the self-test runs on your versions.")
    sentences.append("Every verdict keeps its reason: `ragcourt questions show --dropped`.")
    return section("The judge") + "\n" + textwrap.fill(" ".join(sentences), WIDTH)


def selftest_text(test: SelfTest, *, cases: bool) -> str:
    """The self-test: each case (expected, said, why, agree) when asked, then the score against 90%."""
    lines = [section(f"Judge self-test: {test.model}")]
    if cases:
        rows = [
            [
                result.check,
                result.kind,
                result.expected,
                _said(verdict=result.verdict),
                "yes" if result.agrees else "NO",
                result.reason[:60],
            ]
            for result in test.results
        ]
        lines.append(table(["check", "case", "expected", "judge said", "agree", "reason"], rows))
    verdict = "passed" if test.passed else "FAILED"
    lines.append(f"Score {test.score:.0%} on {len(test.results)} labelled cases (90% needed): {verdict}.")
    return "\n".join(lines)


def _said(*, verdict: bool | None) -> str:
    if verdict is None:
        return "unreadable"
    return "yes/correct" if verdict else "no/incorrect"


def failed_judge_text(test: SelfTest) -> str:
    """Why a judge was refused, with its wrong answers."""
    wrong = [result for result in test.results if not result.agrees]
    examples = "; ".join(f"{result.kind} case judged {_said(verdict=result.verdict)}" for result in wrong[:5])
    score = f"{test.score:.0%}"
    return (
        f"The judge {test.model} agreed with {score} of the labelled cases (90% needed), so its verdicts "
        f"would not be trusted. Wrong: {examples}. Pick another judge with `ragcourt models set judge "
        "MODEL` (gemma4 passed on an 8 GB GPU); `ragcourt models test judge` shows every case."
    )
