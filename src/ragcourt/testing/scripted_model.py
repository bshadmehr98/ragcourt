"""A model client that answers from a script, for tests and examples (design §15.2).

Replies are given in order, or chosen by a function of the request; every request is recorded, so a
test can check exactly what a model was shown. Embeddings come from a ``FakeEmbedder``.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from ragcourt.testing.fake_embedder import FakeEmbedder, fake_tokens
from ragcourt.types import ChatRequest, Embedded, ModelInfo

Replies = Sequence[str] | Callable[[ChatRequest], str]


class ScriptedModel:
    """Implements the ``ModelClient`` protocol from a script; its state is what it was sent."""

    def __init__(self, replies: Replies = (), embedder: FakeEmbedder | None = None) -> None:
        if isinstance(replies, str):
            raise TypeError(
                "ScriptedModel takes a list of replies or a function, not one string: use [reply]."
            )
        self.replies = replies
        self.embedder = embedder or FakeEmbedder()
        self.requests: list[ChatRequest] = []
        self.embedded: list[tuple[str, list[str]]] = []

    def chat(self, request: ChatRequest) -> str:
        """The next scripted reply (or the reply function's answer); the request is recorded first."""
        self.requests.append(request)
        if callable(self.replies):
            return self.replies(request)
        position = len(self.requests) - 1
        if position >= len(self.replies):
            raise LookupError(
                f"ScriptedModel has {len(self.replies)} replies but got request {position + 1}: "
                f"{request.prompt[:80]!r}. Add a reply to the script."
            )
        return self.replies[position]

    def embed(self, model: str, texts: list[str]) -> Embedded:
        """Fake vectors and fake token counts for ``texts``; the call is recorded."""
        self.embedded.append((model, list(texts)))
        return self.embedder.embed(texts)

    def show(self, model: str) -> ModelInfo:
        """The fake embedder's limit as the model's context length."""
        return ModelInfo(model, self.embedder.max_tokens)

    def rerank(self, model: str, query: str, documents: list[str]) -> list[float]:  # noqa: ARG002
        """Scores by words shared with the query: deterministic, no model (any ``model`` scores the same)."""
        words = set(fake_tokens(query))
        return [float(len(words & set(fake_tokens(document)))) for document in documents]
