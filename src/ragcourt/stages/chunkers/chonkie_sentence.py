"""``chonkie.sentence``: chonkie's SentenceChunker, a thin adapter (design §7.4; extra ``chonkie``)."""

# pyright: basic, reportMissingImports=false
from __future__ import annotations

from ragcourt.errors import ExtraMissing
from ragcourt.stages import chunker


@chunker("chonkie.sentence")
def chonkie_sentence(text: str, size: int = 512, overlap: int = 0) -> list[str]:
    """Whole sentences up to ``size`` tokens."""
    try:
        from chonkie import SentenceChunker  # noqa: PLC0415 (an optional extra, imported only when used)
    except ImportError as error:
        raise ExtraMissing("chonkie.sentence needs chonkie: pip install 'ragcourt[chonkie]'.") from error
    return [chunk.text for chunk in SentenceChunker(chunk_size=size, chunk_overlap=overlap).chunk(text)]
