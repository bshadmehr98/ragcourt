"""The ``endpoint`` reranker: a ``/rerank`` route in the Jina and Cohere format (design §7.3, D-015).

vLLM, llama.cpp, TEI, Jina and Cohere serve it; name the model ``endpoint:<name>/<model>``.
"""

from __future__ import annotations

from ragcourt.stages import reranker
from ragcourt.types import ModelClient


@reranker("endpoint")
def endpoint(query: str, candidates: list[str], client: ModelClient, model: str = "") -> list[float]:
    """One relevance score per candidate from the endpoint."""
    return client.rerank(model, query, candidates)
