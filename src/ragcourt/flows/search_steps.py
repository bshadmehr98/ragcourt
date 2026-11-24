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
from ragcourt.core.search import Candidates, Choice, choose, step_specs
from ragcourt.core.stats import Resamples, resamples
from ragcourt.errors import BudgetExceeded
from ragcourt.flows.evaluate import Evaluator
from ragcourt.flows.run_plan import RankOptions, check_budget
from ragcourt.io import run_files
from ragcourt.io.rank_output import board_text, failure_note, weak_spot_note
from ragcourt.io.result_data import board_data
from ragcourt.types.questions import Question
from ragcourt.types.results import Board, Evaluation, PipelineSpec

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
    """The two splits and their resamples."""

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
    scoring: tuple[str, Questions],
    state: SearchState,
    say: Say,
) -> None:
    """One step of the search: evaluate, choose on dev, print the held-out board and what it hides."""
    metric, split = scoring
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
    say(board_text(board_data(leaderboard), _chosen_note(choice)))
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


def _chosen_note(choice: Choice) -> str:
    """The chosen entry, and the rule that chose it among ties (a held-out disagreement is said under
    the board)."""
    note = choice.best.label
    if choice.tied:
        rule = "kept the cheaper, then the higher on dev, then the smaller"
        note += f" (tied on dev with {len(choice.tied)} more; {rule})"
    return note


def draws(questions: list[Question], seed: int, count: int) -> dict[str, Resamples]:
    """The bootstrap resamples of each category, each with its own seed."""
    return {
        name: resamples(len(members), count, f"{seed}:{name}")
        for name, members in by_category(questions).items()
    }
