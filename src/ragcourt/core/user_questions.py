"""The user's own questions: each with a quote, validated by finding it, never judged (§6.3, D-025)."""

from __future__ import annotations

from typing import Any

from ragcourt.core.offsets import find_text
from ragcourt.core.split import question_id
from ragcourt.types.questions import Dropped, Question, Verdict

USER = "user"


def read_user_questions(rows: list[dict[str, Any]], texts: dict[str, str]) -> list[Question | Dropped]:
    """Each row kept as a ``user`` question or rejected with its reason."""
    outcomes: list[Question | Dropped] = []
    for number, row in enumerate(rows):
        if not isinstance(row, dict):  # pyright: ignore[reportUnnecessaryIsInstance] (rows come from a user's file)
            outcomes.append(
                Dropped(USER, "not a JSON object with question and quote", str(row)[:80], "", (), number)
            )
            continue
        outcomes.append(_one(number, row, texts))
    return outcomes


def _one(number: int, row: dict[str, Any], texts: dict[str, str]) -> Question | Dropped:
    question, quote = str(row.get("question", "")).strip(), str(row.get("quote", "")).strip()
    document = row.get("document")
    problem = _missing(question, quote, document, texts)
    found = (
        [] if problem else _places(quote, [str(document)] if document is not None else sorted(texts), texts)
    )
    if not problem and not found:
        problem = "quote not found verbatim"
    if not problem and len(found) > 1:
        names = ", ".join(name for name, _, _ in found[:3])
        problem = f"ambiguous: the quote is found more than once ({names}); quote more of the text"
    if problem:
        return Dropped(USER, problem, question, quote, (), number)
    name, start, end = found[0]
    verdict = Verdict("quote found verbatim", passed=True, reason=f"in {name} at {start}")
    identifier = question_id(name, start, end, question)
    return Question(
        identifier,
        question,
        USER,
        name,
        start,
        end,
        texts[name][start:end],
        verdicts=(verdict,),
        offer=number,
    )


def _missing(question: str, quote: str, document: object, texts: dict[str, str]) -> str | None:
    if not question:
        return "no question"
    if not quote:
        return "no quote: a question without a quote cannot be scored"
    if document is not None and str(document) not in texts:
        return f"no document {document!r}"
    return None


def _places(quote: str, names: list[str], texts: dict[str, str]) -> list[tuple[str, int, int]]:
    places: list[tuple[str, int, int]] = []
    for name in names:
        span = find_text(texts[name], quote)
        if span is not None:
            places.append((name, span[0], span[1]))
        again = find_text(texts[name], quote, span[0] + 1) if span is not None else None
        if again is not None:
            places.append((name, again[0], again[1]))  # twice in one document: ambiguous too
    return places
