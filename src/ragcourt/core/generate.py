"""Writing questions by category and filtering them (design §6.1, §6.2, §6.7, §6.8).

Pure in the sense of design §3.1: the models are callables (prompt in, reply out), and every finished
question or drop is handed to ``record`` as it happens, so the caller can write it to disk and a resumed
run skips the passages already tried (design §10.4).
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field

from ragcourt.core.categories import CATEGORIES
from ragcourt.core.offsets import find_text
from ragcourt.core.question_checks import Context, Models, Outcome, check_question
from ragcourt.core.split import question_id
from ragcourt.core.verdicts import Draft, fill, read_draft
from ragcourt.core.windows import CorpusIndex
from ragcourt.types.questions import Dropped, Offer, Question, Span


@dataclass(frozen=True)
class Wanted:
    """How many questions of which categories, and how hard to try."""

    per_category: int
    categories: tuple[str, ...]
    max_requests_per_question: int
    seed: int


@dataclass(frozen=True)
class Journal:
    """What was done before (a resumed run), and where each new outcome and progress line goes."""

    done: list[Outcome]
    record: Callable[[Outcome], None]
    report: Callable[[Progress], None]


@dataclass
class Progress:
    """Counts for one category while it is written."""

    category: str
    wanted: int
    asked: int = 0
    kept: int = 0
    dropped: dict[str, int] = field(default_factory=dict[str, int])
    finished: bool = False


def ordered_offers(index: CorpusIndex, category: str, seed: int) -> list[Offer]:
    """The category's offers in a fixed, seeded order that takes one passage from each document in turn,
    so one very long document (a changelog) does not supply most of the questions (D-057)."""
    offers = CATEGORIES[category].offers(index)
    random.Random(f"{seed}:{category}").shuffle(offers)  # noqa: S311 (a seeded order, not a secret)
    turn: dict[str, int] = {}
    keyed: list[tuple[int, int, Offer]] = []
    for position, offer in enumerate(offers):
        document = offer.window.document
        turn[document] = turn.get(document, -1) + 1
        keyed.append((turn[document], position, offer))
    return [offer for _, _, offer in sorted(keyed, key=lambda item: item[:2])]


def generate(
    index: CorpusIndex, prompts: dict[str, str], models: Models, wanted: Wanted, journal: Journal
) -> list[Outcome]:
    """Write questions until each category has its count, its offers or its requests run out."""
    outcomes = list(journal.done)
    for category in wanted.categories:
        tried = {item.offer for item in outcomes if _category(item) == category}
        progress = _progress_from(category, wanted.per_category, outcomes)
        limit = wanted.per_category * wanted.max_requests_per_question
        for number, offer in enumerate(ordered_offers(index, category, wanted.seed)):
            if progress.kept >= wanted.per_category or progress.asked >= limit:
                break
            if number in tried:
                continue
            kept = [item for item in outcomes if isinstance(item, Question)]
            outcome = _attempt(category, number, offer, (index, prompts, models), kept)
            outcomes.append(outcome)
            journal.record(outcome)
            _count(progress, outcome)
            journal.report(progress)
        progress.finished = True
        journal.report(progress)
    return outcomes


def _category(item: Outcome) -> str:
    return item.category


def _progress_from(category: str, wanted: int, outcomes: list[Outcome]) -> Progress:
    progress = Progress(category, wanted)
    for item in outcomes:
        if item.category == category:
            _count(progress, item)
    return progress


def _count(progress: Progress, outcome: Outcome) -> None:
    progress.asked += 1
    if isinstance(outcome, Question):
        progress.kept += 1
    else:
        progress.dropped[outcome.reason] = progress.dropped.get(outcome.reason, 0) + 1


def _attempt(category: str, number: int, offer: Offer, context: Context, kept: list[Question]) -> Outcome:
    index, prompts, models = context
    passage = index.text(offer.window)
    twin = index.text(offer.twin) if offer.twin else ""
    template = prompts[f"writer.{category}"]
    reply = models.write(fill(template, passage=passage, term=offer.term or "", twin=twin))
    draft = read_draft(reply)
    if draft is None:
        return Dropped(category, "reply without a question and a quote", reply[:200], "", (), number)
    question = _locate(draft, category, number, offer, index)
    if question is None:
        return Dropped(category, "quote not found verbatim", draft.question, draft.quote, (), number)
    return check_question(question, offer, context, kept)


def _locate(draft: Draft, category: str, number: int, offer: Offer, index: CorpusIndex) -> Question | None:
    text = index.texts[offer.window.document]
    span = find_text(text, draft.quote, offer.window.start) or find_text(text, draft.quote)
    if span is None:
        return None
    start, end = span
    twin = Span(offer.twin.document, offer.twin.start, offer.twin.end) if offer.twin else None
    identifier = question_id(offer.window.document, start, end, draft.question)
    quote = text[start:end]
    return Question(
        identifier,
        draft.question,
        category,
        offer.window.document,
        start,
        end,
        quote,
        "",
        offer.term,
        twin,
        (),
        number,
    )
