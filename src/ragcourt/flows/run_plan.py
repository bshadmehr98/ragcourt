"""The plan of a run, its estimate and the budget: printed and checked before any model call (§10.3)."""

from __future__ import annotations

from dataclasses import dataclass, replace

from ragcourt import stages
from ragcourt.core.pipeline import Settings
from ragcourt.core.plan import Estimate, Workload, estimate
from ragcourt.core.search import Candidates
from ragcourt.errors import BudgetExceeded
from ragcourt.flows.checks import (
    check_budget_values,
    check_categories,
    check_installed,
    check_search,
    check_stages,
)
from ragcourt.flows.questions import QuestionOptions, question_plan
from ragcourt.io.ask import confirm
from ragcourt.io.project import Project
from ragcourt.io.question_file import corpus_hash
from ragcourt.stages.specs import parse_spec
from ragcourt.types import Corpus

QUICK_PER_CATEGORY = 20  # a quick look: too few to name a winner, enough to see the misses (0004)


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
    budget_usd: float | None = None
    yes: bool = False
    resume: bool = False
    quick: bool = False


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
    if options.quick:
        plan["quick"] = {
            "per_category": QUICK_PER_CATEGORY,
            "full_run_minutes": _minutes_after_quick(project, corpus, options, (candidates, counts, llm)),
        }
    return plan, guess


def _minutes_after_quick(
    project: Project, corpus: Corpus, options: RankOptions, work: tuple[Candidates, dict[str, int], int]
) -> float:
    """What the full run would still take after this quick look, whose questions it reuses (estimated)."""
    candidates, counts, llm = work
    full = replace(options.questions, per_category=None)
    _, _, total = question_plan(project, corpus, full)
    still = max(total - QUICK_PER_CATEGORY * len(project.config.questions.categories), 0)
    return round(estimate(Workload(still, total, candidates.embedders, counts, llm)).minutes, 1)


def ready_to_go(project: Project, *, yes: bool, minutes: float, cost: float | None) -> bool:
    """Start without asking with ``--yes``, or for a short, free run that is not the project's first."""
    first_run = not (project.workdir / "runs").exists()
    if yes or (not first_run and minutes <= 1 and cost == 0):
        return True
    return confirm(f"Start this run (about {minutes:.0f} minutes, estimated)?", yes=False)


def budgets(project: Project, options: RankOptions) -> tuple[float | None, float | None]:
    """The time and money budgets: the flags, else ``[budget]`` in ``ragcourt.toml``."""
    budget = project.config.budget
    minutes = options.budget_minutes if options.budget_minutes is not None else budget.minutes
    dollars = options.budget_usd if options.budget_usd is not None else budget.usd
    return minutes, dollars


def estimated_cost(project: Project, embedders: tuple[str, ...], texts: list[str]) -> float | None:
    """Dollars to embed ``texts`` with each endpoint embedder (characters / 4 tokens); local models cost
    nothing; None when an endpoint has no price in ``[prices]`` (unknown, never zero)."""
    tokens = sum(len(text) for text in texts) / 4
    total = 0.0
    for name in embedders:
        if not name.startswith("endpoint:"):
            continue
        price = project.config.prices.get(name)
        if price is None:
            return None
        total += price * tokens / 1_000_000
    return round(total, 4)


def check_cost(budget: float | None, cost: float | None) -> None:
    """Refuse to start a run whose cost is over the budget, or unknown when a budget is set."""
    if budget is None:
        return
    if cost is None:
        raise BudgetExceeded(
            "A money budget is set but an endpoint has no price: add it to [prices]; nothing was run."
        )
    if cost > budget:
        raise BudgetExceeded(
            f"The run would cost about ${cost:.2f}, over the budget of ${budget:g}; nothing was run."
        )


def check_budget(budget: float | None, minutes: float, what: str) -> None:
    """Refuse to start what would go over the time budget."""
    if budget is not None and minutes > budget:
        over = f"{what} would take about {minutes:.1f} minutes, over the budget of {budget:g}"
        raise BudgetExceeded(f"{over}; nothing more was run.")


def check_run(project: Project, options: RankOptions, candidates: Candidates) -> None:
    """Everything ``rank`` is asked to do, before its plan is shown."""
    check_categories(project.config, options.questions.per_category)
    check_search(
        project.config, options.metric or project.config.search.metric, settings_of(project, options).k
    )
    check_stages(candidates)
    check_budget_values(*budgets(project, options))


def check_models(project: Project, options: RankOptions, candidates: Candidates, to_write: int) -> None:
    """After the plan is shown and before any model is called: every Ollama model it names is installed."""
    check_installed(project, _ollama_models(project, options, candidates, to_write))


def _ollama_models(
    project: Project, options: RankOptions, candidates: Candidates, to_write: int
) -> list[str]:
    """The Ollama models this run will call: writer and judge when questions are still to be written, the
    embedders that are model names, and the model of each llm reranker."""
    questions = options.questions
    names: list[str] = []
    if to_write:
        names += [
            *project.role("writer", questions.writer).models,
            *project.role("judge", questions.judge).models,
        ]
    stage_names = stages.names("embedder")
    names += [name for name in candidates.embedders if name.split(":", maxsplit=1)[0] not in stage_names]
    llm = [parse_spec(name) for name in candidates.rerankers if parse_spec(name).name == "llm"]
    names += [str(spec.kwargs().get("model", project.role("reranker").models[0])) for spec in llm]
    return [name for name in dict.fromkeys(names) if not name.startswith("endpoint:")]
