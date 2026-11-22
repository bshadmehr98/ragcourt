"""Typed errors (design §14)."""

import pytest

import ragcourt

ERRORS = [
    "ConfigError",
    "ExtraMissing",
    "ChunkNotInSource",
    "EndpointError",
    "BudgetExceeded",
    "FormatVersionError",
    "GeneratedCodeRejected",
]


@pytest.mark.parametrize("name", ERRORS)
def test_every_error_of_the_design_is_public_and_a_ragcourt_error(name: str) -> None:
    assert name in ragcourt.__all__
    assert issubclass(getattr(ragcourt, name), ragcourt.RagCourtError)


def test_an_endpoint_error_says_whether_to_retry() -> None:
    error = ragcourt.EndpointError("503 from localhost:11434; is Ollama running?", retryable=True)
    assert error.retryable
    assert str(error) == "503 from localhost:11434; is Ollama running?"
