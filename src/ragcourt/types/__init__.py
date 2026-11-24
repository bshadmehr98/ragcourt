"""Layer 0: dataclasses and protocols with no logic (design §2, §3.1, §3.2)."""

from ragcourt.types.documents import Chunk, Corpus, Document, Skipped
from ragcourt.types.models import ChatRequest, ModelClient, ModelInfo
from ragcourt.types.stages import (
    Chunker,
    Embedded,
    Embedder,
    Pipeline,
    Reranker,
    Retriever,
    Search,
    Vector,
)

__all__ = [
    "ChatRequest",
    "Chunk",
    "Chunker",
    "Corpus",
    "Document",
    "Embedded",
    "Embedder",
    "ModelClient",
    "ModelInfo",
    "Pipeline",
    "Reranker",
    "Retriever",
    "Search",
    "Skipped",
    "Vector",
]
