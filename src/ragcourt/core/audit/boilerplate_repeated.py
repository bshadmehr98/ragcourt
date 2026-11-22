"""``boilerplate.repeated``: the chunk is mostly lines repeated across many documents (design §5.1)."""

from __future__ import annotations

import math
from collections import Counter

from ragcourt.types.audit import AuditContext, Finding
from ragcourt.types.documents import Chunk

CODE = "boilerplate.repeated"
MEANING = "is mostly lines that repeat across many documents (headers, footers, menus)"


def repeated_lines(context: AuditContext) -> set[str]:
    """Lines found in at least the set share of documents, and in at least two of them."""
    counts: Counter[str] = Counter()
    for document in context.documents.values():
        counts.update({line.strip() for line in document.text.split("\n") if line.strip()})
    needed = max(2, math.ceil(context.settings.repeated_line_share * len(context.documents)))
    return {line for line, count in counts.items() if count >= needed}


def find(chunks: list[Chunk], context: AuditContext) -> list[Finding]:
    """Chunks whose non-empty lines are at least half (by default) repeated lines."""
    repeated = repeated_lines(context)
    found: list[Finding] = []
    for chunk in chunks:
        lines = [line.strip() for line in chunk.text.split("\n") if line.strip()]
        shared = [line for line in lines if line in repeated]
        if lines and len(shared) / len(lines) >= context.settings.boilerplate_share:
            detail = f"{len(shared)} of {len(lines)} lines repeat, e.g. {shared[0][:60]!r}"
            found.append(Finding(CODE, chunk, detail))
    return found
