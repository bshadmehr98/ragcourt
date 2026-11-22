"""``size.over_limit``: the chunk is longer than the embedder reads, so its end is cut silently (§5.1)."""

from __future__ import annotations

from ragcourt.types.audit import AuditContext, Finding
from ragcourt.types.documents import Chunk

CODE = "size.over_limit"
MEANING = "is longer than the embedder's input limit, so its end is never embedded"


def find(chunks: list[Chunk], context: AuditContext) -> list[Finding]:
    """Chunks over the embedder's limit in force; none when the limit is unknown.

    A measured count can only reach the limit, because the server counts what it read (D-041), so a
    measured count at the limit is a chunk that was cut.
    """
    limit = context.limit
    if limit is None:
        return []
    found: list[Finding] = []
    for chunk, size in zip(chunks, context.sizes, strict=True):
        if context.sizes_measured and size >= limit:
            # A server that cuts silently reports what it read: a count at the limit means it was cut.
            found.append(
                Finding(CODE, chunk, f"at least {limit} tokens, the limit; the rest was cut (measured)")
            )
        elif size > limit:
            found.append(Finding(CODE, chunk, f"{size} tokens over a limit of {limit} (estimated)"))
    return found
