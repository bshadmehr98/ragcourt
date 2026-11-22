"""A project's settings, as read from ``ragcourt.toml`` over the defaults (design §3.3, §11.4). Data only."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ragcourt.types.audit import AuditSettings

CATEGORIES = ("paraphrase", "keyword", "exact_term", "distractor", "negation", "numeric")
ROLES = ("writer", "judge", "embedders", "reranker", "doctor")
DEFAULT_MODELS: dict[str, tuple[str, ...]] = {
    "writer": ("gemma4",),
    "judge": ("gemma4",),
    "embedders": ("nomic-embed-text", "embeddinggemma", "mxbai-embed-large"),
    "reranker": ("gemma4",),
    "doctor": ("gemma4",),
}
DEFAULT_CHUNKERS = (
    "recursive:size=512,overlap=64",
    "recursive:size=256,overlap=32",
    "sentence:size=256",
    "markdown:size=512,overlap=64",
    "fixed:size=256,overlap=32",
)


@dataclass(frozen=True)
class Role:
    """The model or models doing one job, and where that choice came from (D-031)."""

    name: str
    models: tuple[str, ...]
    source: str = "default"  # "default", the ragcourt.toml path, or "flag"


@dataclass(frozen=True)
class Endpoint:
    """An OpenAI-compatible endpoint the user configured; its key is read from an environment variable."""

    name: str
    base_url: str
    api_key_env: str | None = None


@dataclass(frozen=True)
class QuestionSettings:
    """How many questions of which categories (design §6.7, §6.8)."""

    per_category: int = 90
    categories: tuple[str, ...] = CATEGORIES
    min_held_out: int = 30
    window_chars: int = 2000
    max_requests_per_question: int = 6


@dataclass(frozen=True)
class SearchSettings:
    """The candidates of the greedy search and how results are scored (design §8, §10.1)."""

    chunkers: tuple[str, ...] = DEFAULT_CHUNKERS
    retrievers: tuple[str, ...] = ("dense", "bm25", "hybrid")
    rerankers: tuple[str, ...] = ("llm",)
    metric: str = "recall_at_budget"
    k: int = 5
    depth: int = 50
    budget_tokens: int = 400
    resamples: int = 2000


@dataclass(frozen=True)
class Budget:
    """Limits a run must stay under; None means no limit (design §10.3)."""

    usd: float | None = None
    minutes: float | None = None


@dataclass(frozen=True)
class Config:
    """Everything ``ragcourt.toml`` can set, with the defaults filled in."""

    project: Path
    file: Path | None = None
    stages_dir: Path | None = None  # None: the default folder, used only if it exists
    seed: int = 0
    ollama_url: str = "http://localhost:11434"
    roles: dict[str, Role] = field(default_factory=dict[str, Role])
    endpoints: dict[str, Endpoint] = field(default_factory=dict[str, Endpoint])
    prices: dict[str, float] = field(default_factory=dict[str, float])
    questions: QuestionSettings = field(default_factory=QuestionSettings)
    search: SearchSettings = field(default_factory=SearchSettings)
    audit: AuditSettings = field(default_factory=AuditSettings)
    budget: Budget = field(default_factory=Budget)
    prompts_dir: Path | None = None

    def role(self, name: str) -> Role:
        """The role's models: from the file when it set them, else the defaults."""
        return self.roles.get(name, Role(name, DEFAULT_MODELS[name]))

    def stage_folder(self) -> Path:
        """The folder of the user's own stages, set or default."""
        return self.stages_dir or self.project / "ragcourt_stages"
