"""``chonkie.token``: chonkie's TokenChunker, a thin adapter (design §7.4; extra ``chonkie``)."""

# pyright: basic, reportMissingImports=false
from __future__ import annotations

from ragcourt.errors import ExtraMissing
from ragcourt.stages import chunker


@chunker("chonkie.token")
def chonkie_token(text: str, size: int = 512, overlap: int = 64) -> list[str]:
    """Windows of ``size`` tokens of chonkie's default tokenizer."""
    try:
        from chonkie import TokenChunker  # noqa: PLC0415 (an optional extra, imported only when used)
    except ImportError as error:
        raise ExtraMissing("chonkie.token needs chonkie: pip install 'ragcourt[chonkie]'.") from error
    return [chunk.text for chunk in TokenChunker(chunk_size=size, chunk_overlap=overlap).chunk(text)]
