"""What is sent to a model and what comes back (design §11.1). Data and a protocol only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ragcourt.types.stages import Embedded


@dataclass(frozen=True)
class ChatRequest:
    """One chat call: the model, the prompt, whether the reply must be JSON, and its sampling."""

    model: str
    prompt: str
    json_reply: bool = True
    temperature: float = 0.0
    seed: int = 0


@dataclass(frozen=True)
class ModelInfo:
    """What a model server says about a model; None where it does not say."""

    name: str
    context_length: int | None = None
    size_bytes: int | None = None
    digest: str | None = None


class ModelClient(Protocol):
    """The one way ragcourt talks to a model: Ollama, an endpoint, or a fake in tests."""

    def chat(self, request: ChatRequest) -> str:
        """The model's reply as text (``<think>`` blocks already removed)."""
        ...

    def embed(self, model: str, texts: list[str]) -> Embedded:
        """Embed a batch of texts with one model."""
        ...

    def show(self, model: str) -> ModelInfo:
        """What the server says about ``model``: its input limit, size and digest."""
        ...

    def rerank(self, model: str, query: str, documents: list[str]) -> list[float]:
        """One relevance score per document, from a ``/rerank`` endpoint."""
        ...
