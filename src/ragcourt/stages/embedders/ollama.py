"""The ``ollama`` embedder: any Ollama embedding model, with measured token counts (design §7.3, D-041).

The limit in force is measured once: an over-long probe text is embedded and the count Ollama reports is
how much it read. Questions and chunks get the model's documented prefixes (D-042), which the user can
change or turn off with ``query_prefix`` and ``document_prefix``.
"""

from __future__ import annotations

from dataclasses import dataclass

from ragcourt.stages import embedder
from ragcourt.types import Embedded, ModelClient

AUTO = "auto"
# Documented prefixes: (for questions, for passages), by model name without its tag.
KNOWN_PREFIXES = {
    "nomic-embed-text": ("search_query: ", "search_document: "),
    "mxbai-embed-large": ("Represent this sentence for searching relevant passages: ", ""),
    "embeddinggemma": ("task: search result | query: ", "title: none | text: "),
    "snowflake-arctic-embed": ("Represent this sentence for searching relevant passages: ", ""),
    "qwen3-embedding": ("Instruct: Given a question, retrieve passages that answer it\nQuery: ", ""),
}


@dataclass(frozen=True)
class OllamaEmbedder:
    """Implements ``Embedder`` through the one client."""

    client: ModelClient
    model: str
    max_tokens: int | None
    query_prefix: str = ""
    document_prefix: str = ""
    digest: str | None = None
    tokenizer: str = "the model's own, counted by Ollama"

    def embed(self, texts: list[str], *, as_query: bool = False) -> Embedded:
        """Vectors and the token counts Ollama reports, one text per call."""
        prefix = self.query_prefix if as_query else self.document_prefix
        return self.client.embed(self.model, [prefix + text for text in texts])


def known_prefixes(model: str) -> tuple[str, str]:
    """The documented (question, passage) prefixes of a model, or none."""
    return KNOWN_PREFIXES.get(model.split(":", maxsplit=1)[0], ("", ""))


def measured_limit(client: ModelClient, model: str) -> int | None:
    """The input limit in force: what Ollama reads of a text longer than the model's context length."""
    context = client.show(model).context_length
    if not context:
        return None
    counts = client.embed(model, ["x " * (context + 16)]).token_counts
    return counts[0] if counts else context


@embedder("ollama")
def ollama(
    client: ModelClient,
    model: str = "nomic-embed-text",
    query_prefix: str = AUTO,
    document_prefix: str = AUTO,
    limit: int = 0,
) -> OllamaEmbedder:
    """An Ollama model with its limit in force (measured unless given) and its documented prefixes."""
    default_query, default_document = known_prefixes(model)
    return OllamaEmbedder(
        client,
        model,
        limit or measured_limit(client, model),
        default_query if query_prefix == AUTO else query_prefix,
        default_document if document_prefix == AUTO else document_prefix,
        client.show(model).digest,
    )
