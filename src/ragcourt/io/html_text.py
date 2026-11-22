"""Text from an HTML file, shaped like Markdown so the audit reads it the same way (design §4.1).

When the page marks its main content (``<main>``, or ``role="main"``), only that is kept, so a site's
menus and footers do not become part of every document (D-040). Navigation (``<nav>``, ``<aside>``) and
``<head>``, ``<title>``, ``<script>``, ``<style>``, ``<noscript>`` and ``<template>`` are always dropped.
Headings become ``#`` lines, a table becomes ``| a | b |`` lines with a ``| --- |`` line under its first
row, and ``<pre>`` becomes a fenced code block. Outside ``<pre>``, runs of whitespace become one space, as a
browser shows them; inside it, the text stays as written. HTML lets authors leave out ``</tr>``, ``</td>``
and ``</head>``; they are closed where a browser would close them. Inside a table everything is cell text
(a nested table, a heading, a ``<pre>``), so a row stays one line.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

HEADINGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}
PARAGRAPHS = {"p", "div", "section", "article", "header", "footer", "main", "ul", "ol", "blockquote"}
LINES = {"li", "br", "dt", "dd"}
CELLS = {"td", "th"}
# Inside a cell these separate words; inline tags such as <b> do not.
CELL_BREAKS = {*HEADINGS, *PARAGRAPHS, *LINES, *CELLS, "pre", "table", "tr", "caption"}
HIDDEN = {"head", "title", "script", "style", "noscript", "template", "nav", "aside"}
FENCE_MARK = "\x00fence\x00"  # stands for ``` until _tidy, so a literal ``` in the text is not a fence
SPACES = re.compile(r"[ \t\r\n\f]+")


class _TextCollector(HTMLParser):
    """Collects text pieces in reading order; the HTMLParser API works only by subclassing (D-038)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.pieces: list[str] = []
        self.main_pieces: list[str] = []
        self.main_tag: str | None = None
        self.main_depth = 0
        self.hidden_depth = 0
        self.in_pre = False
        self.table_depth = 0
        self.rows_written = 0
        self.row: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.main_tag is None and (tag == "main" or ("role", "main") in attrs):
            self.main_tag = tag
        if tag == self.main_tag:
            self.main_depth += 1
        if tag == "body":
            self.hidden_depth = 0  # a <head> left open ends where the body starts
        elif tag in HIDDEN:
            self.hidden_depth += 1
        elif tag == "table" or self.table_depth:
            self._table_start(tag)
        else:
            self._block_start(tag)

    def handle_endtag(self, tag: str) -> None:
        self._block_end(tag)
        if tag == self.main_tag:
            self.main_depth -= 1
            self.main_tag = self.main_tag if self.main_depth else None

    def _block_end(self, tag: str) -> None:
        if tag in HIDDEN:
            self.hidden_depth = max(0, self.hidden_depth - 1)
        elif tag == "table" and self.table_depth:
            self._table_end()
        elif self.table_depth:
            return
        elif tag in HEADINGS or tag in PARAGRAPHS:
            self._emit("\n\n")
        elif tag == "pre" and self.in_pre:
            self._end_pre()

    def handle_data(self, data: str) -> None:
        if self.hidden_depth:
            return
        if self.in_pre:
            opens_block = self.pieces[-1].endswith(f"{FENCE_MARK}\n") and data.startswith("\n")
            self._emit(data[1:] if opens_block else data)
        elif self.table_depth == 0:
            self._emit(SPACES.sub(" ", data))
        elif self.row:
            self.row[-1] += data
        elif self.row is None and data.strip():
            self._emit(SPACES.sub(" ", data).strip() + "\n")  # a caption, or text between rows

    def close(self) -> None:
        """Finish what the document left open: a row, a ``<pre>``."""
        super().close()
        self._end_row()
        if self.in_pre:
            self._end_pre()

    def _emit(self, text: str) -> None:
        self.pieces.append(text)
        if self.main_depth:
            self.main_pieces.append(text)

    def text(self) -> str:
        """The main content when the page marks it and it holds text; otherwise the whole page."""
        main = "".join(self.main_pieces)
        return main if main.strip() else "".join(self.pieces)

    def _block_start(self, tag: str) -> None:
        if tag in HEADINGS:
            self._emit("\n\n" + "#" * HEADINGS[tag] + " ")
        elif tag == "pre":
            self.in_pre = True
            self._emit(f"\n\n{FENCE_MARK}\n")
        elif tag in PARAGRAPHS:
            self._emit("\n\n")
        elif tag in LINES:
            self._emit("\n")

    def _table_start(self, tag: str) -> None:
        if tag == "table":
            self.table_depth += 1
        if tag == "table" and self.table_depth == 1:
            self._emit("\n\n")
            self.rows_written = 0
        elif self.table_depth == 1 and tag == "tr":
            self._end_row()
            self.row = []
        elif self.table_depth == 1 and tag in CELLS:
            self.row = [] if self.row is None else self.row
            self.row.append("")
        elif tag in CELL_BREAKS and self.row:
            self.row[-1] += " "

    def _table_end(self) -> None:
        self.table_depth -= 1
        if self.table_depth and self.row:
            self.row[-1] += " "  # the end of a nested table separates words, as its start does
        if self.table_depth == 0:
            self._end_row()
            self._emit("\n")

    def _end_row(self) -> None:
        cells = [SPACES.sub(" ", cell).strip() for cell in self.row or []]
        self.row = None
        if not cells:
            return
        self._emit("| " + " | ".join(cells) + " |\n")
        if self.rows_written == 0:
            self._emit("|" + " --- |" * len(cells) + "\n")
        self.rows_written += 1

    def _end_pre(self) -> None:
        self.in_pre = False
        self.pieces[-1] = self.pieces[-1].removesuffix("\n")  # the newline before </pre> is not code
        if self.main_depth and self.main_pieces:
            self.main_pieces[-1] = self.main_pieces[-1].removesuffix("\n")
        self._emit(f"\n{FENCE_MARK}\n\n")


def _tidy(text: str) -> str:
    """Outside code: strip each line, one space between words, at most one blank line. Code stays as is."""
    lines: list[str] = []
    in_code = False
    for line in text.split("\n"):
        if line.strip() == FENCE_MARK:
            in_code = not in_code
            lines.append("```")
        elif in_code:
            lines.append(line)
        elif line.strip() or (lines and lines[-1]):
            lines.append(SPACES.sub(" ", line).strip())
    body = "\n".join(lines).strip("\n")
    return body + "\n" if body else ""


def html_to_text(html: str) -> str:
    """The readable text of an HTML document, with Markdown-style headings, tables and code blocks."""
    collector = _TextCollector()
    collector.feed(html)
    collector.close()
    return _tidy(collector.text())
