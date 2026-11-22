"""Typed errors (design §14). Every message says what happened and what to do."""

from __future__ import annotations


class RagCourtError(Exception):
    """The base of every error ragcourt raises on purpose."""


class ConfigError(RagCourtError):
    """The configuration, a stage name or the user's stage folder is wrong."""


class ExtraMissing(RagCourtError):
    """A stage needs an optional extra that is not installed."""


class ChunkNotInSource(RagCourtError):
    """A chunker returned text that is not found in its document (design §4.2)."""


class EndpointError(RagCourtError):
    """A model endpoint failed; ``retryable`` says whether trying again may help."""

    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


class BudgetExceeded(RagCourtError):
    """The next step of a run would go over the budget the user set."""


class FormatVersionError(RagCourtError):
    """A question or results file was written by a newer ragcourt."""


class GeneratedCodeRejected(RagCourtError):
    """Code a model wrote was not approved, timed out or returned invalid output."""
