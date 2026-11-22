"""A reranker call the server refuses does not end the run (D-057)."""

from ragcourt import EndpointError
from ragcourt.flows.evaluate import _guarded  # pyright: ignore[reportPrivateUsage]
from ragcourt.stages.rerankers.llm import llm
from ragcourt.types import ChatRequest
from ragcourt.types.questions import Dropped


class Refusing:
    """A client whose chat is refused ``times`` times, then answers an order."""

    def __init__(self, times: int) -> None:
        self.times = times
        self.asked: list[ChatRequest] = []

    def chat(self, request: ChatRequest) -> str:
        self.asked.append(request)
        if len(self.asked) <= self.times:
            raise EndpointError("answered 500: token repeat limit reached", retryable=True)
        return '{"order": [2, 1]}'


def test_a_refused_call_is_tried_once_more_with_sampling() -> None:
    client = Refusing(times=1)
    scores = llm("q", ["a", "b"], client, prompt="{{question}} {{passages}}")  # type: ignore[arg-type]
    assert scores[1] > scores[0] and client.asked[1].temperature > 0


def test_a_call_refused_twice_keeps_the_retrieval_order_and_is_counted() -> None:
    failures: list[str] = []

    def rerank(query: str, candidates: list[str]) -> list[float]:
        return llm(query, candidates, Refusing(times=2), prompt="{{question}}")  # type: ignore[arg-type]

    guarded = _guarded(rerank, failures)
    assert guarded is not None and guarded("q", ["a", "b", "c"]) == [3.0, 2.0, 1.0]
    assert len(failures) == 1 and _guarded(None, failures) is None


def test_a_server_that_is_gone_still_stops_the_run() -> None:
    import pytest

    def gone(query: str, candidates: list[str]) -> list[float]:
        raise EndpointError("could not be reached", retryable=False)

    guarded = _guarded(gone, [])
    assert guarded is not None
    with pytest.raises(EndpointError):
        guarded("q", ["a"])


def test_a_refused_draft_is_dropped_with_its_reason() -> None:
    from ragcourt.core import generate

    def refuse(*_: object) -> generate.Outcome:
        raise EndpointError("answered 500: token repeat limit reached", retryable=True)

    original = generate._attempt  # pyright: ignore[reportPrivateUsage]
    generate._attempt = refuse  # type: ignore[assignment]  # pyright: ignore[reportPrivateUsage]
    try:
        outcome = generate._safe_attempt("keyword", 3, None, None, [])  # type: ignore[arg-type]  # pyright: ignore[reportPrivateUsage]
    finally:
        generate._attempt = original  # pyright: ignore[reportPrivateUsage]
    assert isinstance(outcome, Dropped)
    assert outcome.reason == "the model's server refused the call" and outcome.offer == 3
