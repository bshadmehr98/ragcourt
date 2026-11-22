"""Questions, their gold quotes and the verdicts about them (design §6). Data only."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Verdict:
    """One check on a question: which check, whether it passed, and why (in the judge's words or ours)."""

    check: str
    passed: bool
    reason: str
    by: str = "code"  # "code", or the judge model's name


@dataclass(frozen=True)
class Span:
    """A ``[start, end)`` span of one document."""

    document: str
    start: int
    end: int


@dataclass(frozen=True)
class Question:
    """A question with its gold quote: a span of one document that answers it (design §6.5)."""

    id: str
    question: str
    category: str
    document: str
    start: int
    end: int
    quote: str
    split: str = ""  # "dev" or "held-out", set after generation
    term: str | None = None  # the exact term of an exact_term question
    twin: Span | None = None  # the misleading passage of a distractor question
    verdicts: tuple[Verdict, ...] = ()
    offer: int = -1  # which passage offer it came from, so a resumed run skips it


@dataclass(frozen=True)
class Dropped:
    """A question that was written and dropped, with the reason and every verdict before it."""

    category: str
    reason: str
    question: str
    quote: str
    verdicts: tuple[Verdict, ...] = ()
    offer: int = -1


@dataclass(frozen=True)
class Window:
    """A passage offered to the question writer: a span cut at paragraph boundaries (design §6.1)."""

    document: str
    start: int
    end: int


@dataclass(frozen=True)
class Offer:
    """A window offered for one category, with the term or twin passage that category needs."""

    window: Window
    term: str | None = None
    twin: Window | None = None


@dataclass(frozen=True)
class QuestionSet:
    """Kept questions, dropped ones, and the counts by category and reason."""

    questions: list[Question] = field(default_factory=list[Question])
    dropped: list[Dropped] = field(default_factory=list[Dropped])


PASS_MARK = 0.9  # the judge must agree with 90% of its labelled cases (D-026)
EXPECTED_TRUE = {"correct", "yes"}


@dataclass(frozen=True)
class CaseResult:
    """One labelled case: what was expected, what the judge said and why, and whether they agree."""

    check: str
    kind: str
    question: str
    expected: str
    verdict: bool | None
    reason: str

    @property
    def agrees(self) -> bool:
        """True when the judge's verdict is the expected one."""
        return self.verdict is (self.expected in EXPECTED_TRUE)


@dataclass(frozen=True)
class SelfTest:
    """The judge's results on every case, its score, and whether it passed."""

    model: str
    prompts: dict[str, str]  # prompt name -> hash, so a changed prompt is tested again
    results: list[CaseResult]

    @property
    def score(self) -> float:
        """The share of cases the judge agreed with."""
        return sum(result.agrees for result in self.results) / len(self.results) if self.results else 0.0

    @property
    def passed(self) -> bool:
        """True at 90% agreement or more."""
        return self.score >= PASS_MARK
