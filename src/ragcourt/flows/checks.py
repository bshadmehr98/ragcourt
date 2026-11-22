"""Settings checked before anything runs (D-057): a wrong value is one message before the plan, never a
traceback after the questions are written.
"""

from __future__ import annotations

from ragcourt import stages
from ragcourt.core.categories import CATEGORIES
from ragcourt.core.metrics import METRIC_FUNCTIONS
from ragcourt.core.search import Candidates
from ragcourt.errors import ConfigError
from ragcourt.io.project import Project
from ragcourt.stages.specs import check_params, parse_spec
from ragcourt.types.config import Config


def check_categories(config: Config, per_category: int | None = None) -> None:
    """Every category named in ``[questions]`` exists, and the counts make sense."""
    if per_category is not None:
        _at_least("--questions", per_category, 0)
    unknown = [name for name in config.questions.categories if name not in CATEGORIES]
    if unknown:
        raise ConfigError(
            f"Unknown question categories {unknown}; the categories are {', '.join(CATEGORIES)}."
        )
    settings = config.questions
    _at_least("questions.per_category", settings.per_category, 0)
    _at_least("questions.min_held_out", settings.min_held_out, 1)
    _at_least("questions.window_chars", settings.window_chars, 200)
    _at_least("questions.max_requests_per_question", settings.max_requests_per_question, 1)


def check_search(config: Config, metric: str, k: int) -> None:
    """The metric exists; k, depth, the token budget and the resamples are in range."""
    if metric not in METRIC_FUNCTIONS:
        raise ConfigError(f"Unknown metric {metric!r}; the metrics are {', '.join(METRIC_FUNCTIONS)}.")
    search = config.search
    _at_least("k", k, 1)
    _at_least("search.depth", search.depth, k)
    _at_least("search.budget_tokens", search.budget_tokens, 1)
    _at_least("search.resamples", search.resamples, 100)


def check_stages(candidates: Candidates) -> None:
    """Every retriever and reranker named exists and takes the parameters given."""
    for kind, specs in (("retriever", candidates.retrievers), ("reranker", candidates.rerankers)):
        for text in specs:
            spec = parse_spec(text)
            check_params(stages.find(kind, spec.name).function, spec, injected=("client",))


def check_budget_values(minutes: float | None, dollars: float | None) -> None:
    """A budget, when set, is above zero."""
    for name, value in (("--budget-minutes", minutes), ("--budget-usd", dollars)):
        if value is not None and value <= 0:
            raise ConfigError(f"{name} must be above 0, not {value:g}.")


def check_installed(project: Project, models: list[str]) -> None:
    """Every Ollama model the run will call is installed, before the first question is written."""
    if not models:
        return
    if not project.client.ollama_answers():
        where = project.config.ollama_url
        raise ConfigError(f"Ollama does not answer at {where}: start it (`ollama serve`) or set ollama_url.")
    installed = project.client.ollama.installed()
    missing = [name for name in models if name not in installed]
    if missing:
        pulls = "; ".join(f"`ollama pull {name}`" for name in missing)
        raise ConfigError(
            f"Not installed in Ollama: {', '.join(missing)}. Install with {pulls}, or choose another model "
            "with `ragcourt models set ROLE MODEL`."
        )


def _at_least(name: str, value: int, low: int) -> None:
    if value < low:
        raise ConfigError(f"{name} must be at least {low}, not {value}.")
