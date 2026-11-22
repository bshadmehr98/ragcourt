"""The ``endpoint`` embedder: any OpenAI-compatible ``/embeddings`` (design §7.3).

Endpoints do not report per-text token counts, so sizes are estimated and labelled so; the input limit is
unknown unless given as ``max_tokens``.
"""

from __future__ import annotations

from dataclasses import dataclass

from ragcourt.stages import embedder
from ragcourt.types import Embedded, ModelClient


@dataclass(frozen=True)
class EndpointEmbedder:
    """Implements ``Embedder`` through the one client, for a model named ``endpoint:<name>/<model>``."""

    client: ModelClient
    model: str
    max_tokens: int | None = None
    query_prefix: str = ""
    document_prefix: str = ""
    tokenizer: str = "unknown (sizes estimated)"

    def embed(self, texts: list[str], *, as_query: bool = False) -> Embedded:
        """Vectors from the endpoint; token counts are not available."""
        prefix = self.query_prefix if as_query else self.document_prefix
        return self.client.embed(self.model, [prefix + text for text in texts])


@embedder("endpoint")
def endpoint(
    client: ModelClient,
    model: str = "",
    max_tokens: int = 0,
    query_prefix: str = "",
    document_prefix: str = "",
) -> EndpointEmbedder:
    """An endpoint model, e.g. ``endpoint:openai/text-embedding-3-small``."""
    return EndpointEmbedder(client, model, max_tokens or None, query_prefix, document_prefix)
