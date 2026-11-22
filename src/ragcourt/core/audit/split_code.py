"""``split.code``: the chunk holds part, but not all, of a code block (design §5.1)."""

from __future__ import annotations

from ragcourt.types.audit import AuditContext, Finding
from ragcourt.types.documents import Chunk

CODE = "split.code"
MEANING = "holds part of a code block but not all of it"


def find(chunks: list[Chunk], context: AuditContext) -> list[Finding]:
    """Chunks that overlap a fenced or indented code block without holding all of it."""
    found: list[Finding] = []
    for chunk in chunks:
        for start, end in context.structures[chunk.document].code_blocks:
            overlaps = chunk.start < end and start < chunk.end
            whole = chunk.start <= start and end <= chunk.end
            if overlaps and not whole:
                lines = context.documents[chunk.document].text[start:end].count("\n") + 1
                found.append(Finding(CODE, chunk, f"cuts a code block of {lines} lines at offset {start}"))
                break
    return found
