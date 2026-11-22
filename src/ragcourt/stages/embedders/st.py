"""``st``: a sentence-transformers model in-process, a thin adapter (design §7.4; extra ``local``)."""

# pyright: basic, reportMissingImports=false
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ragcourt.errors import ExtraMissing
from ragcourt.stages import embedder
from ragcourt.types import Embedded


@dataclass(frozen=True)
class SentenceTransformerEmbedder:
    """Implements ``Embedder`` with a sentence-transformers model and its own tokenizer."""

    model: str
    encoder: Any
    max_tokens: int | None
    tokenizer: str = "the model's own (sentence-transformers)"

    def embed(self, texts: list[str], *, as_query: bool = False) -> Embedded:  # noqa: ARG002
        """Vectors and the tokenizer's counts (cut at the limit, like the model reads them)."""
        vectors = [list(map(float, vector)) for vector in self.encoder.encode(texts)]
        counts = [len(self.encoder.tokenizer(text)["input_ids"]) for text in texts]
        return Embedded(vectors, counts)


@embedder("st")
def st(model: str = "sentence-transformers/all-MiniLM-L6-v2") -> SentenceTransformerEmbedder:
    """A local sentence-transformers model (downloaded by that library on first use)."""
    try:
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415 (an optional extra)
    except ImportError as error:
        raise ExtraMissing(
            "The st embedder needs sentence-transformers: pip install 'ragcourt[local]'."
        ) from error
    encoder = SentenceTransformer(model)
    return SentenceTransformerEmbedder(model, encoder, encoder.max_seq_length)
