"""``context.no_heading``: the chunk lies under a heading it does not contain (design §5.1)."""

from __future__ import annotations

from ragcourt.types.audit import AuditContext, Finding
from ragcourt.types.documents import Chunk

CODE = "context.no_heading"
MEANING = "lies under a heading that is not in the chunk, so the chunk lost its topic"


def find(chunks: list[Chunk], context: AuditContext) -> list[Finding]:
    """Chunks whose nearest heading above them is not inside them."""
    found: list[Finding] = []
    for chunk in chunks:
        headings = context.structures[chunk.document].headings
        above = [span for span in headings if span[0] < chunk.start]
        inside = [span for span in headings if chunk.start <= span[0] < chunk.end]
        if not above or (inside and inside[0][0] == chunk.start):
            continue
        start, end = above[-1]
        heading = context.documents[chunk.document].text[start:end].split("\n")[0].strip()
        if heading.lstrip("# ") not in chunk.text:
            found.append(Finding(CODE, chunk, f"under {heading!r}"))
    return found
