"""Layer 0: dataclasses and protocols with no logic (design §2, §3.1, §3.2)."""

from ragcourt.types.documents import Corpus, Document, Skipped
from ragcourt.types.models import ChatRequest, Embedded, ModelClient
from ragcourt.types.stages import Chunker, Embedder, Reranker, Retriever, Search, Vector

__all__ = [
    "ChatRequest",
    "Chunker",
    "Corpus",
    "Document",
    "Embedded",
    "Embedder",
    "ModelClient",
    "Reranker",
    "Retriever",
    "Search",
    "Skipped",
    "Vector",
]
