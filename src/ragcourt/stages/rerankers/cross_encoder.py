"""``cross-encoder``: a sentence-transformers cross-encoder in-process (design §7.4; extra ``local``)."""

# pyright: basic, reportMissingImports=false
from __future__ import annotations

from ragcourt.errors import ExtraMissing
from ragcourt.stages import reranker


@reranker("cross-encoder")
def cross_encoder(
    query: str, candidates: list[str], model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
) -> list[float]:
    """One relevance score per candidate."""
    try:
        from sentence_transformers import CrossEncoder  # noqa: PLC0415 (an optional extra)
    except ImportError as error:
        raise ExtraMissing(
            "The cross-encoder needs sentence-transformers: pip install 'ragcourt[local]'."
        ) from error
    pairs = [(query, text) for text in candidates]
    return [float(score) for score in CrossEncoder(model).predict(pairs)]
