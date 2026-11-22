"""What the audit finds and what it needs to know (design §5). Data only."""

from __future__ import annotations

from dataclasses import dataclass, field

from ragcourt.types.documents import Chunk, Document


@dataclass(frozen=True)
class AuditSettings:
    """The thresholds of the checks (D-024), all settable in ``ragcourt.toml`` under ``[audit]``."""

    tiny_tokens: int = 20
    near_duplicate_jaccard: float = 0.9
    repeated_line_share: float = 0.3
    boilerplate_share: float = 0.5


@dataclass(frozen=True)
class Structure:
    """The blocks of one document the checks look at, as ``(start, end)`` spans."""

    headings: tuple[tuple[int, int], ...] = ()
    tables: tuple[tuple[int, int], ...] = ()
    code_blocks: tuple[tuple[int, int], ...] = ()


@dataclass(frozen=True)
class AuditContext:
    """Everything a check may read besides the chunks: the documents, their structure, the sizes."""

    documents: dict[str, Document]
    structures: dict[str, Structure]
    sizes: list[int]
    sizes_measured: bool
    limit: int | None
    settings: AuditSettings = field(default_factory=AuditSettings)


@dataclass(frozen=True)
class Finding:
    """One chunk flagged by one check, with a short detail in plain words."""

    code: str
    chunk: Chunk
    detail: str


@dataclass(frozen=True)
class SizeSummary:
    """The sizes of a set of chunks, in tokens, and whether they were measured or estimated."""

    median: int
    p95: int
    largest: int
    measured: bool

    @property
    def label(self) -> str:
        """``measured`` or ``estimated``, as every output says (design §4.3)."""
        return "measured" if self.measured else "estimated"


@dataclass(frozen=True)
class ChunkerAudit:
    """The audit of one chunker over a corpus."""

    chunker: str
    chunks: list[Chunk]
    dropped_empty: int
    size: SizeSummary
    findings: list[Finding]


@dataclass(frozen=True)
class AuditReport:
    """The whole audit: which documents, how sizes were counted, and each chunker's result."""

    documents: int
    skipped: list[tuple[str, str]]
    embedder: str
    sizes_measured: bool
    limit: int | None
    note: str
    results: list[ChunkerAudit]
