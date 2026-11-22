"""``size.tiny``: the chunk has fewer tokens than the threshold (20 by default) (design §5.1)."""

from __future__ import annotations

from ragcourt.types.audit import AuditContext, Finding
from ragcourt.types.documents import Chunk

CODE = "size.tiny"
MEANING = "is too small to carry an answer on its own"


def find(chunks: list[Chunk], context: AuditContext) -> list[Finding]:
    """Chunks under ``tiny_tokens`` tokens (measured or estimated, as labelled)."""
    label = "measured" if context.sizes_measured else "estimated"
    threshold = context.settings.tiny_tokens
    return [
        Finding(CODE, chunk, f"{size} tokens ({label})")
        for chunk, size in zip(chunks, context.sizes, strict=True)
        if size < threshold
    ]
