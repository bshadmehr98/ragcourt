"""``split.table``: the chunk holds part, but not all, of a table's rows (design §5.1)."""

from __future__ import annotations

from ragcourt.types.audit import AuditContext, Finding
from ragcourt.types.documents import Chunk

CODE = "split.table"
MEANING = "holds part of a table but not all of its rows"


def find(chunks: list[Chunk], context: AuditContext) -> list[Finding]:
    """Chunks that overlap a table without holding all of it."""
    found: list[Finding] = []
    for chunk in chunks:
        for start, end in context.structures[chunk.document].tables:
            overlaps = chunk.start < end and start < chunk.end
            whole = chunk.start <= start and end <= chunk.end
            if overlaps and not whole:
                rows = context.documents[chunk.document].text[start:end].count("\n") + 1
                found.append(Finding(CODE, chunk, f"cuts a table of {rows} rows at offset {start}"))
                break
    return found
