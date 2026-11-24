"""The steps of the greedy search as ``rank`` runs them: one board per step, the choice on dev (§10.1).

Each step evaluates its pipelines, chooses on dev questions, prints the held-out leaderboard and what the
choice hides, and is stopped before it starts when it would pass the time budget (design §10.3).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from ragcourt.core.leaderboard import Scoring, board, by_category, weak_spots
from ragcourt.core.search import Candidates, choose, step_specs
from ragcourt.core.stats import Resamples, resamples
from ragcourt.errors import BudgetExceeded
from ragcourt.flows.blames import blame_external
from ragcourt.flows.evaluate import Evaluator
from ragcourt.flows.external import External, external_data, run_external
from ragcourt.flows.run_plan import RankOptions, check_budget
from ragcourt.io import run_files
from ragcourt.io.rank_output import board_text, chosen_note, failure_note, placed_note, weak_spot_note
from ragcourt.io.result_data import board_data
from ragcourt.types.questions import Question
from ragcourt.types.results import Blame, Board, Evaluation, PipelineSpec

Say = Callable[[str], None]


@dataclass
class SearchState:
    """What the search has done so far."""

    steps: list[dict[str, object]] = field(default_factory=list[dict[str, object]])
    boards: list[Board] = field(default_factory=list[Board])
    measured: list[Evaluation] = field(default_factory=list[Evaluation])
    best: PipelineSpec | None = None


@dataclass(frozen=True)
class Questions:
    """The two splits, their resamples, and the metric they are scored by."""

    metric: str
    dev: list[Question]
    held_out: list[Question]
    dev_draws: dict[str, Resamples]
    held_draws: dict[str, Resamples]


def guard(
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


def step_search(
    step: str,
    evaluator: Evaluator,
    candidates: Candidates,
    split: Questions,
    state: SearchState,
    say: Say,
) -> None:
    """One step of the search: evaluate, choose on dev, print the held-out board and what it hides."""
    metric = split.metric
    config = evaluator.project.config
    run_files.log_progress(evaluator.folder, {"step": step, "event": "start"})
    say(f"\nStep {len(state.steps) + 1} of 4: {step}s …")
    evaluations = [evaluator.evaluate(spec) for spec in step_specs(step, state.best, candidates)]
    state.measured += evaluations
    choice = choose(evaluations, split.dev, metric, split.dev_draws)
    state.best = choice.best
    leaderboard_scoring = Scoring(split.held_out, metric, config.questions.min_held_out, split.held_draws)
    leaderboard = board(step, evaluations, leaderboard_scoring)
    state.boards.append(leaderboard)
    say(board_text(board_data(leaderboard), chosen_note(choice.best.label, len(choice.tied))))
    for evaluation in [item for item in evaluations if item.costs.rerank_failures]:
        say(failure_note(evaluation.spec.label, evaluation.costs.rerank_failures))
    chosen = next(item for item in evaluations if item.spec == choice.best)
    for spot in weak_spots(evaluations, chosen, leaderboard_scoring):
        say(weak_spot_note(spot.category, spot.chosen_mean, spot.better, spot.better_mean))
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


def pipeline_step(
    evaluator: Evaluator, name: str, split: Questions, state: SearchState, say: Say
) -> tuple[External, list[Blame]]:
    """The last step of a run with ``--pipeline``: the user's pipeline on a board beside the search's choice
    (when there was a search), its misses blamed. It is one fixed system: nothing is chosen on dev."""
    run_files.log_progress(evaluator.folder, {"step": "pipeline", "event": "start"})
    say(f"\nYour pipeline {name}: {len(evaluator.questions)} questions …")
    external = run_external(evaluator, name)
    beside = [item for item in state.measured if item.spec == state.best]
    evaluations = [external.evaluation, *beside]
    minimum = evaluator.project.config.questions.min_held_out
    scoring = Scoring(split.held_out, split.metric, minimum, split.held_draws)
    leaderboard = board("pipeline", evaluations, scoring)
    say(board_text(board_data(leaderboard), None))
    say(placed_note(external_data(external)))
    blames = blame_external(evaluator, external, state.measured, state.best, split.held_out)
    state.boards.append(leaderboard)
    state.measured.append(external.evaluation)
    labels = [evaluation.spec.label for evaluation in evaluations]
    chosen = external.evaluation.spec.label
    state.steps.append({"step": "pipeline", "evaluated": labels, "chosen": chosen, "tied_on_dev": []})
    run_files.log_progress(evaluator.folder, {"step": "pipeline", "event": "end"})
    return external, blames


def draws(questions: list[Question], seed: int, count: int) -> dict[str, Resamples]:
    """The bootstrap resamples of each category, each with its own seed."""
    return {
        name: resamples(len(members), count, f"{seed}:{name}")
        for name, members in by_category(questions).items()
    }
