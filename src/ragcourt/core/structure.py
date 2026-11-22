"""Headings, tables and code blocks of a document, found by line rules (design §5.1).

Markdown is the model: ATX headings (``# Title``), setext headings (a line underlined with ``===`` or
``---``; reStructuredText's ``~~~`` and ``^^^`` too), pipe tables (two or more lines starting with ``|``),
fenced code (```````` or ``~~~``) and indented code (four spaces after a blank line). HTML arrives in this
shape already (design §4.1). Nothing inside fenced code is read as a heading or a table.
"""

from __future__ import annotations

import re

from ragcourt.types.audit import Structure

Span = tuple[int, int]
Line = tuple[int, str]  # the offset where a line starts, and the line without its newline
ATX = re.compile(r"#{1,6}[ \t]+\S")
UNDERLINE = re.compile(r"(={3,}|-{3,}|~{3,}|\^{3,})[ \t]*")
FENCE = re.compile(r"[ \t]{0,3}(```|~~~)")


def structure_of(text: str) -> Structure:
    """The headings, tables and code blocks of ``text``."""
    lines = _lines(text)
    fenced = _fenced_blocks(lines)
    outside = [line for line in lines if not _inside(line[0], fenced)]
    headings = _headings(outside)
    tables = _table_runs(outside)
    code = sorted(fenced + _indented_blocks(outside))
    return Structure(tuple(headings), tuple(tables), tuple(code))


def _lines(text: str) -> list[Line]:
    lines: list[Line] = []
    offset = 0
    for line in text.split("\n"):
        lines.append((offset, line))
        offset += len(line) + 1
    return lines


def _inside(offset: int, blocks: list[Span]) -> bool:
    return any(start <= offset < end for start, end in blocks)


def _fenced_blocks(lines: list[Line]) -> list[Span]:
    blocks: list[Span] = []
    opened: tuple[int, str] | None = None
    for offset, line in lines:
        match = FENCE.match(line)
        if match and opened is None:
            opened = (offset, match.group(1))
        elif opened is not None and line.strip() == opened[1]:
            blocks.append((opened[0], offset + len(line)))
            opened = None
    if opened is not None:
        last_offset, last_line = lines[-1]
        blocks.append((opened[0], last_offset + len(last_line)))
    return blocks


def _headings(lines: list[Line]) -> list[Span]:
    headings: list[Span] = []
    for number, (offset, line) in enumerate(lines):
        if ATX.match(line):
            headings.append((offset, offset + len(line)))
        elif number + 1 < len(lines) and _is_setext(line, lines[number + 1]):
            under_offset, under = lines[number + 1]
            headings.append((offset, under_offset + len(under)))
    return headings


def _is_setext(title: str, under: Line) -> bool:
    plain_title = bool(title.strip()) and not title.lstrip().startswith(("|", "#"))
    return plain_title and bool(UNDERLINE.fullmatch(under[1].strip()))


def _table_runs(lines: list[Line]) -> list[Span]:
    runs: list[Span] = []
    run: list[Line] = []
    for offset, line in [*lines, (-1, "")]:
        if offset >= 0 and line.lstrip().startswith("|"):
            run.append((offset, line))
            continue
        if len(run) >= 2:
            runs.append((run[0][0], run[-1][0] + len(run[-1][1])))
        run = []
    return runs


def _indented_blocks(lines: list[Line]) -> list[Span]:
    blocks: list[Span] = []
    previous_blank = True
    start: int | None = None
    end = 0
    for offset, line in lines:
        indented = line.startswith(("    ", "\t")) and bool(line.strip())
        if indented and (start is not None or previous_blank):
            start = offset if start is None else start
            end = offset + len(line)
        elif line.strip() and start is not None:
            blocks.append((start, end))
            start = None
        previous_blank = not line.strip()
    if start is not None:
        blocks.append((start, end))
    return blocks
