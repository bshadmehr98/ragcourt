"""Writing the question set for people: counts by category, drops by reason, every verdict (§6.6, §6.8)."""

from __future__ import annotations

import textwrap

from ragcourt.io.terminal import legend, section, table
from ragcourt.types.questions import Dropped, Question, Verdict

LEGEND = {
    "dev": "questions used to choose between pipelines (a third of each category)",
    "held-out": "questions every reported number comes from (two thirds)",
    "too few to rank": "a category with fewer held-out questions than the minimum; never averaged in",
}


def summary_text(questions: list[Question], dropped: list[Dropped], min_held_out: int, *, quiet: bool) -> str:
    """Kept questions per category and split, drops per reason, and which categories are too few to rank."""
    categories = sorted({item.category for item in [*questions, *dropped]})
    rows: list[list[object]] = []
    for category in categories:
        members = [question for question in questions if question.category == category]
        held_out = sum(1 for question in members if question.split == "held-out")
        lost = sum(1 for item in dropped if item.category == category)
        status = "ok" if held_out >= min_held_out else "too few to rank"
        rows.append([category, len(members), len(members) - held_out, held_out, lost, status])
    lines = [section("Questions"), table(["category", "kept", "dev", "held-out", "dropped", "status"], rows)]
    lines += _drops(dropped)
    if not quiet:
        lines += ["", legend(LEGEND)]
    return "\n".join(lines) + "\n"


def _drops(dropped: list[Dropped]) -> list[str]:
    counts: dict[tuple[str, str], list[Dropped]] = {}
    for item in dropped:
        counts.setdefault((item.category, item.reason), []).append(item)
    if not counts:
        return []
    rows = [
        [category, reason, len(items), items[0].question[:50]]
        for (category, reason), items in sorted(counts.items())
    ]
    return [section("Dropped, by reason"), table(["category", "reason", "count", "example"], rows)]


def show_text(
    questions: list[Question], dropped: list[Dropped], *, show_dropped: bool, reason: str | None
) -> str:
    """Every question (or dropped one) with its quote and each verdict's reason."""
    lines: list[str] = []
    if show_dropped:
        for item in dropped:
            if reason is None or reason in item.reason:
                lines += [
                    f"[{item.category}] DROPPED: {item.reason}",
                    *_body(item.question, item.quote, item.verdicts),
                ]
        return "\n".join(lines) + "\n" if lines else "No dropped questions match.\n"
    for question in questions:
        where = f"{question.document} [{question.start}:{question.end}]"
        lines += [
            f"{question.id} [{question.category}, {question.split}] {where}",
            *_body(question.question, question.quote, question.verdicts),
        ]
    return "\n".join(lines) + "\n" if lines else "No questions yet: run `ragcourt questions FOLDER`.\n"


def _body(question: str, quote: str, verdicts: tuple[Verdict, ...]) -> list[str]:
    lines = [
        f"  Q: {question}",
        textwrap.fill(f"quote: {quote}", 100, initial_indent="  ", subsequent_indent="     "),
    ]
    for verdict in verdicts:
        mark = "pass" if verdict.passed else "FAIL"
        lines.append(f"  - {verdict.check}: {mark} ({verdict.by}) {verdict.reason}")
    lines.append("")
    return lines
