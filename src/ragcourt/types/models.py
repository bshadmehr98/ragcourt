"""What is sent to a model and what comes back (design §11.1). Data and a protocol only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ragcourt.types.stages import Vector


@dataclass(frozen=True)
class ChatRequest:
    """One chat call: the model, the prompt, and whether the reply must be JSON."""

    model: str
    prompt: str
    json_reply: bool = True


@dataclass(frozen=True)
class Embedded:
    """Vectors for a batch of texts, with the token counts the model reported, if it did."""

    vectors: list[Vector]
    token_counts: list[int] | None


class ModelClient(Protocol):
    """The one way ragcourt talks to a model: Ollama, an endpoint, or a fake in tests."""

    def chat(self, request: ChatRequest) -> str:
        """The model's reply as text (``<think>`` blocks already removed)."""
        ...

    def embed(self, model: str, texts: list[str]) -> Embedded:
        """Embed a batch of texts with one model."""
        ...
