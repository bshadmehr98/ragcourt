"""``chonkie.recursive``: chonkie's RecursiveChunker, a thin adapter (design §7.4; extra ``chonkie``)."""

# pyright: basic, reportMissingImports=false
from __future__ import annotations

from ragcourt.errors import ExtraMissing
from ragcourt.stages import chunker


@chunker("chonkie.recursive")
def chonkie_recursive(text: str, size: int = 512) -> list[str]:
    """chonkie's recursive rules, up to ``size`` tokens."""
    try:
        from chonkie import RecursiveChunker  # noqa: PLC0415 (an optional extra, imported only when used)
    except ImportError as error:
        raise ExtraMissing("chonkie.recursive needs chonkie: pip install 'ragcourt[chonkie]'.") from error
    return [chunk.text for chunk in RecursiveChunker(chunk_size=size).chunk(text)]
