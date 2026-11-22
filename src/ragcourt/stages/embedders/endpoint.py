"""The ``endpoint`` embedder: any OpenAI-compatible ``/embeddings`` (design §7.3, §4.3).

Endpoints do not report per-text token counts. With ``tokenizer="tiktoken:<encoding>"`` (the ``tokens``
extra) sizes are counted exactly; otherwise they are estimated and labelled so. The input limit is unknown
unless given as ``max_tokens``.
"""

# pyright: basic, reportMissingImports=false
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ragcourt.errors import ConfigError, ExtraMissing
from ragcourt.stages import embedder
from ragcourt.types import Embedded, ModelClient

Counter = Callable[[str], int]


@dataclass(frozen=True)
class EndpointEmbedder:
    """Implements ``Embedder`` through the one client, for a model named ``endpoint:<name>/<model>``."""

    client: ModelClient
    model: str
    max_tokens: int | None = None
    query_prefix: str = ""
    document_prefix: str = ""
    tokenizer: str = "unknown (sizes estimated)"
    counter: Counter | None = None
    server: str = ""  # the endpoint's URL and model, so another server gets its own cache

    def embed(self, texts: list[str], *, as_query: bool = False) -> Embedded:
        """Vectors from the endpoint, and counts when a tokenizer was named."""
        prefix = self.query_prefix if as_query else self.document_prefix
        sent = [prefix + text for text in texts]
        vectors = self.client.embed(self.model, sent).vectors
        counts = [self.counter(text) for text in sent] if self.counter else None
        return Embedded(vectors, counts)


def tiktoken_counter(name: str) -> Counter:
    """Token counts from a tiktoken encoding (the ``tokens`` extra)."""
    try:
        import tiktoken  # noqa: PLC0415 (an optional extra, imported only when used)
    except ImportError as error:
        raise ExtraMissing("Counting with tiktoken needs it: pip install 'ragcourt[tokens]'.") from error
    encoding = tiktoken.get_encoding(name)
    return lambda text: len(encoding.encode(text))


@embedder("endpoint")
def endpoint(
    client: ModelClient,
    model: str = "",
    max_tokens: int = 0,
    query_prefix: str = "",
    document_prefix: str = "",
    tokenizer: str = "",
) -> EndpointEmbedder:
    """An endpoint model, e.g. ``endpoint:openai/text-embedding-3-small``."""
    if tokenizer and not tokenizer.startswith("tiktoken:"):
        raise ConfigError(f"tokenizer {tokenizer!r}: write tiktoken:<encoding>, e.g. tiktoken:cl100k_base.")
    counter = tiktoken_counter(tokenizer.removeprefix("tiktoken:")) if tokenizer else None
    label = f"{tokenizer} (measured)" if tokenizer else "unknown (sizes estimated)"
    server = client.show(model).name
    return EndpointEmbedder(
        client, model, max_tokens or None, query_prefix, document_prefix, label, counter, server
    )
