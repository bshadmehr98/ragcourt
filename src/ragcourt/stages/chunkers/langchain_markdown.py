"""``langchain.markdown``: LangChain's MarkdownTextSplitter, a thin adapter (design §7.4)."""

# pyright: basic, reportMissingImports=false
from __future__ import annotations

from ragcourt.errors import ExtraMissing
from ragcourt.stages import chunker


@chunker("langchain.markdown")
def langchain_markdown(text: str, size: int = 2000, overlap: int = 200) -> list[str]:
    """Markdown-aware pieces of at most ``size`` characters."""
    try:
        from langchain_text_splitters import MarkdownTextSplitter  # noqa: PLC0415 (an optional extra)
    except ImportError as error:
        raise ExtraMissing("langchain.markdown needs it: pip install 'ragcourt[langchain]'.") from error
    return MarkdownTextSplitter(chunk_size=size, chunk_overlap=overlap).split_text(text)
