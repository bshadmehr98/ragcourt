"""``langchain.recursive``: LangChain's RecursiveCharacterTextSplitter, a thin adapter (§7.4)."""

# pyright: basic, reportMissingImports=false
from __future__ import annotations

from ragcourt.errors import ExtraMissing
from ragcourt.stages import chunker


@chunker("langchain.recursive")
def langchain_recursive(text: str, size: int = 2000, overlap: int = 200) -> list[str]:
    """Pieces of at most ``size`` characters, cut at paragraphs, lines, then words."""
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter  # noqa: PLC0415 (an optional extra)
    except ImportError as error:
        raise ExtraMissing("langchain.recursive needs it: pip install 'ragcourt[langchain]'.") from error
    return RecursiveCharacterTextSplitter(chunk_size=size, chunk_overlap=overlap).split_text(text)
