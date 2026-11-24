"""``rank``: the plan first, then questions, the greedy search, leaderboards, blame and the results file.

Design §8 to §10. Nothing calls a model before the plan is printed (D-030); a long run shows its progress
and every finished question, embedding and pipeline is kept, so ``--resume`` continues it (design §10.4).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from ragcourt.core.plan import Estimate
from ragcourt.core.relevance import token_map
from ragcourt.core.search import STEPS, Candidates
from ragcourt.errors import ConfigError
from ragcourt.flows.blames import blame_misses
from ragcourt.flows.evaluate import Evaluator
from ragcourt.flows.external import pipeline_step
from ragcourt.flows.questions import ensure_questions
from ragcourt.flows.results import results_data
from ragcourt.flows.run_plan import (
    RankOptions,
    budgets,
    candidates_of,
    check_budget,
    check_cost,
    check_models,
    check_run,
    estimated_cost,
    make_plan,
    ready_to_go,
    settings_of,
)
from ragcourt.flows.search_steps import Questions, SearchState, draws, guard, step_search
from ragcourt.io import run_files
from ragcourt.io.project import Project
from ragcourt.io.rank_output import plan_text
from ragcourt.types import Corpus
from ragcourt.types.questions import Question

Say = Callable[[str], None]


def run_rank(project: Project, corpus: Corpus, options: RankOptions, say: Say) -> Path | None:
    """The whole run; returns the run's folder, or None when the user did not start it."""
    if not corpus.documents:
        raise ConfigError("No documents to rank: give a folder of .md, .txt, .rst, .html or .pdf files.")
    started = time.monotonic()
    candidates = candidates_of(project, options)
    check_run(project, options, candidates)
    evaluator = _evaluator(project, corpus, options, [])
    counts = {chunker: len(evaluator.chunked(chunker).chunks) for chunker in candidates.chunkers}
    plan, guess = make_plan(project, corpus, options, candidates, counts)
    say(plan_text(plan, guess))
    minutes, dollars = budgets(project, options)
    cost = estimated_cost(project, candidates.embedders, _texts(evaluator, candidates))
    say(
        "Estimated cost: unknown (an endpoint has no price)."
        if cost is None
        else f"Estimated cost: at most ${cost:.2f}."
    )
    check_budget(minutes, guess.minutes, "the whole run")
    check_cost(dollars, cost)
    if not ready_to_go(project, yes=options.yes, minutes=guess.minutes, cost=cost):
        say("Not started. Run again with --yes to start without asking.")
        return None
    check_models(project, options, candidates, int(plan["questions"]["to_write"]))  # type: ignore[index]
    folder = _folder(project, plan, resume=options.resume, say=say)
    run_files.log_progress(folder, {"step": "questions", "event": "start"})
    questions = ensure_questions(project, corpus, options.questions, say)
    _check_questions(questions)
    evaluator = _evaluator(project, corpus, options, questions, folder, evaluator)
    options = replace(options, budget_minutes=minutes)  # the configured budget holds in every step
    return _search(evaluator, candidates, (plan, guess), options, (say, started))


def _texts(evaluator: Evaluator, candidates: Candidates) -> list[str]:
    texts: list[str] = []
    for chunker in candidates.chunkers:
        texts += [chunk.text for chunk in evaluator.chunked(chunker).chunks]
    return texts


def _folder(project: Project, plan: dict[str, object], *, resume: bool, say: Say) -> Path:
    """The unfinished run with the same plan when resuming, else a new one; either way, said."""
    earlier = run_files.unfinished_run(project.workdir, plan)
    if resume and earlier is not None:
        say(f"Resuming {earlier.name}.")
        return earlier
    if resume:
        say("No unfinished run has this plan (documents, models or settings changed): starting a new one.")
    elif earlier is not None:
        say(f"An unfinished run with this plan exists ({earlier.name}); `--resume` continues it.")
    return run_files.new_run(project.workdir, plan)


def _check_questions(questions: list[Question]) -> None:
    """Refuse to rank on nothing: pipelines are chosen on dev questions and reported on held-out ones."""
    splits = {question.split for question in questions}
    if "dev" not in splits or "held-out" not in splits:
        raise ConfigError(
            f"Only {len(questions)} questions were kept: too few to choose on some and report on others. "
            "Ask for more (--questions N), add your own (--questions-file), or check the drops "
            "(`ragcourt questions show --dropped`)."
        )


def _evaluator(
    project: Project,
    corpus: Corpus,
    options: RankOptions,
    questions: list[Question],
    folder: Path | None = None,
    earlier: Evaluator | None = None,
) -> Evaluator:
    texts = {document.id: document.text for document in corpus.documents}
    built = Evaluator(
        project, corpus, questions, settings_of(project, options), token_map(texts), folder or project.workdir
    )
    if earlier is not None:
        built.chunkings = earlier.chunkings  # chunked for the plan already
    return built


def _search(
    evaluator: Evaluator,
    candidates: Candidates,
    planned: tuple[dict[str, object], Estimate],
    options: RankOptions,
    output: tuple[Say, float],
) -> Path:
    plan, guess = planned
    say, started = output
    config = evaluator.project.config
    dev = [question for question in evaluator.questions if question.split == "dev"]
    held = [question for question in evaluator.questions if question.split == "held-out"]
    count = config.search.resamples
    split = Questions(dev, held, draws(dev, config.seed, count), draws(held, config.seed, count))
    state = SearchState()
    for step in () if options.no_search else STEPS:
        guard(evaluator.folder, options, (step, guess.step_minutes.get(step, 0.0), started), (plan, state))
        step_search(step, evaluator, candidates, (str(plan["metric"]), split), state, say)
    extra: dict[str, object] = {}
    if options.pipeline:
        # The run is then about the user's pipeline: its misses are blamed, the search is the comparison.
        subject, blames, extra = pipeline_step(
            evaluator, options.pipeline, state, (str(plan["metric"]), split), say
        )
    elif state.best is None:
        raise ConfigError("No pipeline was evaluated; check the candidates in [search].")
    else:
        subject, blames = state.best, blame_misses(evaluator, state.best, state.measured, split.held_out)
    minutes = (time.monotonic() - started) / 60
    searched = (state.steps, state.boards, state.measured)
    results = results_data(evaluator, planned, searched, subject, blames, minutes)
    run_files.write_results(evaluator.folder, {**results, **extra})
    run_files.log_progress(evaluator.folder, {"step": "done", "event": "end"})
    return evaluator.folder
