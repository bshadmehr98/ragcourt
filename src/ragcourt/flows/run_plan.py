"""The plan of a run, its estimate and the budget: printed and checked before any model call (§10.3)."""

from __future__ import annotations

from dataclasses import dataclass

from ragcourt.core.pipeline import Settings
from ragcourt.core.plan import Estimate, Workload, estimate
from ragcourt.core.search import Candidates
from ragcourt.errors import BudgetExceeded
from ragcourt.flows.questions import QuestionOptions, question_plan
from ragcourt.io.ask import confirm
from ragcourt.io.project import Project
from ragcourt.io.question_file import corpus_hash
from ragcourt.types import Corpus


@dataclass(frozen=True)
class RankOptions:
    """What the command line asked for; None means the configuration's value."""

    questions: QuestionOptions
    metric: str | None = None
    k: int | None = None
    embedders: tuple[str, ...] | None = None
    chunkers: tuple[str, ...] | None = None
    retrievers: tuple[str, ...] | None = None
    rerankers: tuple[str, ...] | None = None
    budget_minutes: float | None = None
    yes: bool = False
    resume: bool = False


def candidates_of(project: Project, options: RankOptions) -> Candidates:
    """The stages the search may try: flags first, then ``ragcourt.toml``, then the defaults."""
    search = project.config.search
    return Candidates(
        options.embedders or project.role("embedders").models,
        options.chunkers or search.chunkers,
        options.retrievers or search.retrievers,
        options.rerankers or search.rerankers,
    )


def settings_of(project: Project, options: RankOptions) -> Settings:
    """k, depth and the token budget of ``recall_at_budget``."""
    search = project.config.search
    return Settings(options.k or search.k, search.depth, search.budget_tokens)


def make_plan(
    project: Project, corpus: Corpus, options: RankOptions, candidates: Candidates, counts: dict[str, int]
) -> tuple[dict[str, object], Estimate]:
    """The plan (everything that decides the results, so a resumed run must match it) and the estimate."""
    reused, to_write, total = question_plan(project, corpus, options.questions)
    llm = sum(1 for name in candidates.rerankers if name.split(":", maxsplit=1)[0] == "llm")
    guess = estimate(Workload(to_write, total, candidates.embedders, counts, llm))
    flag = ",".join(options.embedders) if options.embedders else None
    roles = [project.role("writer", options.questions.writer), project.role("judge", options.questions.judge)]
    roles += [project.role("embedders", flag), project.role("reranker")]
    lists = {
        "embedders": list(candidates.embedders),
        "chunkers": list(candidates.chunkers),
        "retrievers": list(candidates.retrievers),
        "rerankers": list(candidates.rerankers),
    }
    plan: dict[str, object] = {
        "corpus_hash": corpus_hash(corpus.documents),
        "documents": len(corpus.documents),
        "questions": {"reused": reused, "to_write": to_write, "total": total},
        "roles": [{"role": role.name, "models": list(role.models), "source": role.source} for role in roles],
        "candidates": lists,
        "chunks": counts,
        "metric": options.metric or project.config.search.metric,
        "settings": vars(settings_of(project, options)),
        "seed": project.config.seed,
    }
    return plan, guess


def ready_to_go(project: Project, *, yes: bool, minutes: float) -> bool:
    """Start without asking with ``--yes``, or for a short run that is not the project's first."""
    first_run = not (project.workdir / "runs").exists()
    if yes or (not first_run and minutes <= 1):
        return True
    return confirm(f"Start this run (about {minutes:.0f} minutes, estimated)?", yes=False)


def check_budget(budget: float | None, minutes: float, what: str) -> None:
    """Refuse to start what would go over the time budget."""
    if budget is not None and minutes > budget:
        over = f"{what} would take about {minutes:.1f} minutes, over the budget of {budget:g}"
        raise BudgetExceeded(f"{over}; nothing more was run.")
