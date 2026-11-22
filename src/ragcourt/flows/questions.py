"""Building the question set: reuse, resume or write it, with the judge checked first (§6, §10.4).

Used by ``ragcourt questions`` and ``ragcourt rank``. Before any model is called the roles and the judge are
explained (D-030); the judge must pass its self-test (D-026); every question or drop is written as it
finishes, so ``--resume`` loses nothing; splits are assigned when the set is complete.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from ragcourt.core.generate import Journal, Progress, Wanted, generate
from ragcourt.core.offsets import find_text
from ragcourt.core.question_checks import Models, Outcome
from ragcourt.core.split import assign_splits
from ragcourt.core.user_questions import read_user_questions
from ragcourt.core.windows import index_corpus
from ragcourt.flows.checks import check_categories
from ragcourt.flows.judge import JUDGE_PROMPTS, check_judge, judge_line
from ragcourt.io import question_file
from ragcourt.io.narration import judge_text, roles_text
from ragcourt.io.project import Project
from ragcourt.io.prompts import load_prompts
from ragcourt.types import Corpus
from ragcourt.types.questions import Dropped, Question

Say = Callable[[str], None]
REPORT_EVERY = 10  # a progress line every this many questions asked, and when a category is done


@dataclass(frozen=True)
class QuestionOptions:
    """What the command line asked for."""

    per_category: int | None = None
    judge: str | None = None
    writer: str | None = None
    questions_file: Path | None = None
    resume: bool = True


def ensure_questions(project: Project, corpus: Corpus, options: QuestionOptions, say: Say) -> list[Question]:
    """The question set for this corpus: reused when complete and unchanged, else resumed or written."""
    check_categories(project.config, options.per_category)
    header = _header(project, corpus, options)
    existing = question_file.read_questions(project.workdir)
    done = _reusable(existing, header, corpus, say)
    if (
        existing is not None
        and done is not None
        and existing[0].get("complete")
        and _same(existing[0], header)
    ):
        say(f"Reusing {len(existing[1])} questions from {project.workdir / question_file.QUESTIONS}.")
        say(judge_line(project, project.role("judge", options.judge).models[0]))
        return existing[1]
    question_file.start_files(project.workdir, header)
    for outcome in done or []:
        question_file.append(project.workdir, outcome)
    outcomes = _write(project, corpus, options, done or [], say)
    questions = assign_splits([item for item in outcomes if isinstance(item, Question)], project.config.seed)
    dropped = [item for item in outcomes if isinstance(item, Dropped)]
    question_file.finish(
        project.workdir, {**header, "complete": True, "dropped": drop_counts(dropped)}, questions
    )
    return questions


def question_plan(project: Project, corpus: Corpus, options: QuestionOptions) -> tuple[bool, int, int]:
    """Before any model call: whether the set is reused, how many questions are still to write, the total."""
    header = _header(project, corpus, options)
    existing = question_file.read_questions(project.workdir)
    own = len(question_file.read_rows(options.questions_file)) if options.questions_file else 0
    wanted = header["per_category"] * len(header["categories"])
    if existing is not None and existing[0].get("complete") and _same(existing[0], header):
        return True, 0, len(existing[1])
    have = (
        len(existing[1])
        if existing is not None and _same(existing[0], header, ignore=("per_category",))
        else 0
    )
    return False, max(wanted - have, 0), wanted + own


def _header(project: Project, corpus: Corpus, options: QuestionOptions) -> dict[str, Any]:
    settings = project.config.questions
    return {
        "corpus_hash": question_file.corpus_hash(corpus.documents),
        "writer": ", ".join(project.role("writer", options.writer).models),
        "judge": ", ".join(project.role("judge", options.judge).models),
        "seed": project.config.seed,
        "per_category": settings.per_category if options.per_category is None else options.per_category,
        "categories": list(settings.categories),
        "user_questions": str(options.questions_file) if options.questions_file else None,
        "prompts": {name: prompt.hash for name, prompt in load_prompts(project.config.prompts_dir).items()},
        "complete": False,
    }


def _same(old: dict[str, Any], new: dict[str, Any], *, ignore: tuple[str, ...] = ()) -> bool:
    keys = (
        "corpus_hash",
        "writer",
        "judge",
        "seed",
        "per_category",
        "categories",
        "user_questions",
        "prompts",
    )
    return all(old.get(key) == new.get(key) for key in keys if key not in ignore)


def _reusable(
    existing: tuple[dict[str, Any], list[Question], list[Dropped]] | None,
    header: dict[str, Any],
    corpus: Corpus,
    say: Say,
) -> list[Outcome] | None:
    """What an earlier set gives this run: all of it when only unfinished or smaller, its still-valid
    questions when the documents changed, nothing when the models, prompts, seed or categories changed."""
    if existing is None:
        return None
    old, questions, dropped = existing
    if not _same(old, header, ignore=("corpus_hash", "per_category")):
        say("The writer, judge, prompts, seed or categories changed: writing a new question set.")
        return None
    if old.get("corpus_hash") == header["corpus_hash"]:
        return [*questions, *dropped]
    texts = {document.id: document.text for document in corpus.documents}
    kept = revalidate(questions, texts)
    say(f"The documents changed: {len(kept)} of {len(questions)} questions still hold.")
    return list(kept)


def revalidate(questions: list[Question], texts: dict[str, str]) -> list[Question]:
    """Questions whose quote is still in their document, at its new place."""
    kept: list[Question] = []
    for question in questions:
        text = texts.get(question.document)
        span = find_text(text, question.quote) if text is not None else None
        if span is not None and text is not None:
            # The twin passage may have moved or changed with the documents: it is no longer pointed at.
            kept.append(
                replace(question, start=span[0], end=span[1], quote=text[span[0] : span[1]], twin=None)
            )
    return kept


def _write(
    project: Project, corpus: Corpus, options: QuestionOptions, done: list[Outcome], say: Say
) -> list[Outcome]:
    outcomes = list(done)
    if options.questions_file is not None:
        outcomes += _user_questions(project, corpus, options.questions_file, done)
    settings = project.config.questions
    wanted = Wanted(
        settings.per_category if options.per_category is None else options.per_category,
        settings.categories,
        settings.max_requests_per_question,
        project.config.seed,
    )
    if not wanted.per_category or not wanted.categories:
        say("No questions to write: only your own questions are used; the writer and judge are not called.")
        return outcomes
    writer = project.role("writer", options.writer)
    judge = project.role("judge", options.judge)
    say(roles_text([writer, judge]))
    prompts = load_prompts(project.config.prompts_dir)
    hashes = {name: prompts[name].hash for name in JUDGE_PROMPTS}
    say(judge_text(judge, hashes, [prompt.name for prompt in prompts.values() if prompt.replaced]))
    check_judge(project, judge.models[0], {name: prompt.text for name, prompt in prompts.items()}, say)
    models = Models(
        project.chat(writer.models[0]),
        project.chat(writer.models[0], json_reply=False),
        project.chat(judge.models[0]),
        judge.models[0],
    )
    index = index_corpus(corpus.documents, settings.window_chars)
    journal = Journal(outcomes, lambda item: question_file.append(project.workdir, item), _reporter(say))
    return generate(index, {name: prompt.text for name, prompt in prompts.items()}, models, wanted, journal)


def _user_questions(project: Project, corpus: Corpus, path: Path, done: list[Outcome]) -> list[Outcome]:
    if any(item.category == "user" for item in done):
        return []
    texts = {document.id: document.text for document in corpus.documents}
    outcomes = read_user_questions(question_file.read_rows(path), texts)
    for outcome in outcomes:
        question_file.append(project.workdir, outcome)
    return outcomes


def _reporter(say: Say) -> Callable[[Progress], None]:
    first_seen: dict[str, tuple[float, int]] = {}  # per category: when this run first saw it, and its asks

    def report(progress: Progress) -> None:
        since, asked_before = first_seen.setdefault(progress.category, (time.monotonic(), progress.asked))
        if not progress.finished and progress.asked % REPORT_EVERY:
            return
        dropped = sum(progress.dropped.values())
        pace = (time.monotonic() - since) / max(progress.asked - asked_before, 1)
        asks_per_kept = progress.asked / progress.kept if progress.kept else 2.0  # this category's own yield
        left = max(progress.wanted - progress.kept, 0) * pace * asks_per_kept
        counts = f"{progress.kept}/{progress.wanted} kept, {dropped} dropped, {progress.asked} asked"
        tail = "done" if progress.finished else f"about {left / 60:.0f} min left in this category"
        say(f"  {progress.category}: {counts}; {tail}")

    return report


def drop_counts(dropped: list[Dropped]) -> dict[str, dict[str, int]]:
    """How many questions each category lost, by reason."""
    counts: dict[str, dict[str, int]] = {}
    for item in dropped:
        by_reason = counts.setdefault(item.category, {})
        by_reason[item.reason] = by_reason.get(item.reason, 0) + 1
    return counts
