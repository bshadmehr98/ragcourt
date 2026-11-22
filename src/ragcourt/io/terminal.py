"""Plain-text tables and legends for the terminal (design §13.2): no colour, aligned columns."""

from __future__ import annotations

import re
from collections.abc import Sequence


def table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    """An aligned table: text left, numbers right, a rule under the header."""
    cells: list[list[str]] = []
    for row in rows:
        cells.append([str(cell) for cell in row])
    widths = [len(header) for header in headers]
    for row in cells:
        for column, cell in enumerate(row):
            widths[column] = max(widths[column], len(cell))
    numeric = [bool(cells) and _numeric_column(cells, column) for column in range(len(headers))]
    lines = [_line(list(headers), widths, [False] * len(headers)), "  ".join("-" * width for width in widths)]
    lines += [_line(row, widths, numeric) for row in cells]
    return "\n".join(lines)


def _numeric_column(cells: list[list[str]], column: int) -> bool:
    return all(_is_number(row[column]) for row in cells)


def _is_number(cell: str) -> bool:
    return cell.replace(".", "", 1).replace("%", "").replace("-", "", 1).isdigit()


def _line(cells: Sequence[str], widths: list[int], right: list[bool]) -> str:
    parts = [
        cell.rjust(width) if align else cell.ljust(width)
        for cell, width, align in zip(cells, widths, right, strict=True)
    ]
    return "  ".join(parts).rstrip()


def legend(entries: dict[str, str]) -> str:
    """The words an output used, each with the rule behind it, one per line."""
    width = max((len(word) for word in entries), default=0)
    lines = ["Legend:"] + [f"  {word.ljust(width)}  {meaning}" for word, meaning in entries.items()]
    return "\n".join(lines)


# Characters that can move the cursor, hide a line or reorder text on a terminal (C0 but newline and tab,
# DEL, C1, and the bidirectional controls of "Trojan Source").
HIDDEN = {
    *range(0x09),
    *range(0x0B, 0x20),
    *range(0x7F, 0xA0),
    0x200E,
    0x200F,
    *range(0x202A, 0x202F),
    *range(0x2066, 0x206A),
}
PRINTABLE = {code: f"\\x{code:02x}" if code < 0x100 else f"\\u{code:04x}" for code in HIDDEN}


def printable(text: str) -> str:
    """``text`` with every character that could hide or rewrite what is shown written as an escape."""
    return text.translate(PRINTABLE)


DESIGN_REFERENCE = re.compile(r"\s*\((?:design |brief )?(?:§|D-)[^)]*\)")


def for_people(text: str | None) -> str:
    """A module docstring as help text: without references into the design, which users do not have."""
    return DESIGN_REFERENCE.sub("", text or "").replace("``", "`")


def plural(count: int, word: str) -> str:
    """``1 document``, ``2 documents``."""
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def section(title: str) -> str:
    """A section heading for terminal output."""
    return f"\n{title}\n{'=' * len(title)}"
