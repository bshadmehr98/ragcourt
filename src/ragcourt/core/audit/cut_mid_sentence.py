"""``cut.mid_sentence``: the chunk ends where the source goes on with the same sentence (design §5.1)."""

from __future__ import annotations

import re

from ragcourt.text_units import ends_sentence
from ragcourt.types.audit import AuditContext, Finding
from ragcourt.types.documents import Chunk

CODE = "cut.mid_sentence"
MEANING = "ends in the middle of a sentence that the next chunk finishes"
BLOCK_END = re.compile(r"[ \t]*(\n[ \t]*\n|\n#|\n[ \t]*[-*+] |\n[ \t]*\d+\. |\n[ \t]*\||\n```|\n~~~|$)")


def find(chunks: list[Chunk], context: AuditContext) -> list[Finding]:
    """Chunks whose last visible character does not close a sentence and whose block goes on."""
    found: list[Finding] = []
    for chunk in chunks:
        text = context.documents[chunk.document].text
        if ends_sentence(chunk.text) or BLOCK_END.match(text, chunk.end):
            continue
        if _in_any(chunk.end, context.structures[chunk.document].code_blocks):
            continue  # a cut inside code is split.code's business
        words = chunk.text.rstrip().split()
        tail = " ".join(words[-4:])
        found.append(Finding(CODE, chunk, f"ends with …{tail!r}"))
    return found


def _in_any(offset: int, blocks: tuple[tuple[int, int], ...]) -> bool:
    return any(start < offset < end for start, end in blocks)
