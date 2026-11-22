"""The ``llm`` reranker: a chat model orders the top candidates in one listwise call (design §7.3, D-015).

Ollama has no rerank route, so a local chat model ranks the passages; the prompt is ``reranker.llm.txt``,
given by ragcourt. Candidates past ``top`` keep their order below the reranked ones. A reply that cannot be
read keeps the retriever's order; a refused call is tried once more with sampling (temperature 0.7).
"""

from __future__ import annotations

import json
import re
from typing import cast

from ragcourt.errors import EndpointError
from ragcourt.stages import reranker
from ragcourt.types import ChatRequest, ModelClient

ORDER = re.compile(r"\{.*\}", re.DOTALL)


def read_order(reply: str, count: int) -> list[int]:
    """The passage numbers (0-based) in the reply's order, each once, missing ones appended in order."""
    numbers: list[int] = []
    for item in _listed(reply):
        if isinstance(item, int) and 1 <= item <= count and item - 1 not in numbers:
            numbers.append(item - 1)
    return numbers + [position for position in range(count) if position not in numbers]


def _listed(reply: str) -> list[object]:
    match = ORDER.search(reply)
    if not match:
        return []
    try:
        data: object = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    order = cast(dict[str, object], data).get("order") if isinstance(data, dict) else None
    return cast(list[object], order) if isinstance(order, list) else []


@reranker("llm")
def llm(
    query: str,
    candidates: list[str],
    client: ModelClient,
    model: str = "gemma4",
    prompt: str = "",
    top: int = 20,
) -> list[float]:
    """Scores from the model's order of the first ``top`` candidates."""
    head = candidates[:top]
    passages = "\n\n".join(f"[{number}] {text[:1200]}" for number, text in enumerate(head, start=1))
    text = prompt.replace("{{question}}", query).replace("{{passages}}", passages)
    try:
        reply = client.chat(ChatRequest(model, text))
    except EndpointError as error:  # e.g. Ollama's "token repeat limit reached": another sample may pass
        if not error.retryable:
            raise
        reply = client.chat(ChatRequest(model, text, temperature=0.7, seed=1))
    order = read_order(reply, len(head))
    scores = [0.0] * len(candidates)
    for place, position in enumerate(order):
        scores[position] = float(len(candidates) * 2 - place)
    for position in range(len(head), len(candidates)):
        scores[position] = float(len(candidates) - position)
    return scores
