"""``rank``: the plan first, then questions, the greedy search, leaderboards, blame and the results file.

Design §8 to §10. Nothing calls a model before the plan is printed (D-030); a long run shows its progress
and every finished question, embedding and pipeline is kept, so ``--resume`` continues it (design §10.4).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from pathlib import Path

from ragcourt.core.leaderboard import Scoring, board, by_category
from ragcourt.core.plan import Estimate
from ragcourt.core.relevance import token_map
from ragcourt.core.search import STEPS, Candidates, Choice, choose, step_specs
from ragcourt.core.stats import Resamples, resamples
from ragcourt.errors import BudgetExceeded, ConfigError
from ragcourt.flows.blames import blame_misses
from ragcourt.flows.evaluate import Evaluator
from ragcourt.flows.questions import ensure_questions
from ragcourt.flows.results import results_data
from ragcourt.flows.run_plan import (
    RankOptions,
    budgets,
    candidates_of,
    check_budget,
    check_cost,
    estimated_cost,
    make_plan,
    ready_to_go,
    settings_of,
)
from ragcourt.io import run_files
from ragcourt.io.project import Project
from ragcourt.io.rank_output import board_text, plan_text
from ragcourt.io.result_data import board_data
from ragcourt.types import Corpus
from ragcourt.types.questions import Question
from ragcourt.types.results import Board, Evaluation, PipelineSpec

Say = Callable[[str], None]


def run_rank(project: Project, corpus: Corpus, options: RankOptions, say: Say) -> Path | None:
    """The whole run; returns the run's folder, or None when the user did not start it."""
    if not corpus.documents:
        raise ConfigError("No documents to rank: give a folder of .md, .txt, .rst or .html files.")
    started = time.monotonic()
    candidates = candidates_of(project, options)
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


@dataclass
class SearchState:
    """What the search has done so far."""

    steps: list[dict[str, object]] = field(default_factory=list[dict[str, object]])
    boards: list[Board] = field(default_factory=list[Board])
    measured: list[Evaluation] = field(default_factory=list[Evaluation])
    best: PipelineSpec | None = None


@dataclass(frozen=True)
class Questions:
    """The two splits and their resamples."""

    dev: list[Question]
    held_out: list[Question]
    dev_draws: dict[str, Resamples]
    held_draws: dict[str, Resamples]


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
    split = Questions(dev, held, _draws(dev, config.seed, count), _draws(held, config.seed, count))
    state = SearchState()
    for step in STEPS:
        _guard(evaluator.folder, options, (step, guess.step_minutes.get(step, 0.0), started), (plan, state))
        _step(step, evaluator, candidates, (str(plan["metric"]), split), state, say)
    if state.best is None:
        raise ConfigError("No pipeline was evaluated; check the candidates in [search].")
    blames = blame_misses(evaluator, state.best, state.measured, split.held_out)
    minutes = (time.monotonic() - started) / 60
    searched = (state.steps, state.boards, state.measured)
    run_files.write_results(
        evaluator.folder, results_data(evaluator, planned, searched, state.best, blames, minutes)
    )
    run_files.log_progress(evaluator.folder, {"step": "done", "event": "end"})
    return evaluator.folder


def _guard(
    folder: Path,
    options: RankOptions,
    timing: tuple[str, float, float],
    context: tuple[dict[str, object], SearchState],
) -> None:
    """Stop before a step that would go over the time budget, keeping what is finished (§10.3)."""
    step, step_minutes, started = timing
    plan, state = context
    spent = (time.monotonic() - started) / 60
    try:
        check_budget(options.budget_minutes, spent + step_minutes, f"the {step} step")
    except BudgetExceeded as error:
        done = ", ".join(str(item["step"]) for item in state.steps) or "none"
        run_files.write_partial(folder, {"plan": plan, "steps": state.steps, "stopped_before": step})
        raise BudgetExceeded(f"{error} Finished steps: {done}; kept in {folder}.") from error


def _step(
    step: str,
    evaluator: Evaluator,
    candidates: Candidates,
    scoring: tuple[str, Questions],
    state: SearchState,
    say: Say,
) -> None:
    metric, split = scoring
    config = evaluator.project.config
    run_files.log_progress(evaluator.folder, {"step": step, "event": "start"})
    say(f"\nStep {len(state.steps) + 1} of 4: {step}s …")
    evaluations = [evaluator.evaluate(spec) for spec in step_specs(step, state.best, candidates)]
    state.measured += evaluations
    choice = choose(evaluations, split.dev, metric, split.dev_draws)
    state.best = choice.best
    leaderboard = board(
        step, evaluations, Scoring(split.held_out, metric, config.questions.min_held_out, split.held_draws)
    )
    state.boards.append(leaderboard)
    say(board_text(board_data(leaderboard), _chosen_note(choice, leaderboard)))
    labels = [evaluation.spec.label for evaluation in evaluations]
    state.steps.append(
        {
            "step": step,
            "evaluated": labels,
            "chosen": choice.best.label,
            "tied_on_dev": [s.label for s in choice.tied],
        }
    )
    run_files.log_progress(evaluator.folder, {"step": step, "event": "end", "chosen": choice.best.label})


def _chosen_note(choice: Choice, leaderboard: Board) -> str:
    """The chosen entry, and why it may differ from the held-out leader."""
    note = choice.best.label
    if choice.tied:
        note += (
            f" (tied on dev with {len(choice.tied)} more; kept the cheaper, then smaller, then first listed)"
        )
    if leaderboard.winner is not None and leaderboard.winner != choice.best:
        note += "\nDev and held-out questions disagree here; with this few questions the choice is uncertain."
    return note


def _draws(questions: list[Question], seed: int, count: int) -> dict[str, Resamples]:
    return {
        name: resamples(len(members), count, f"{seed}:{name}")
        for name, members in by_category(questions).items()
    }
