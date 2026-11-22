"""Text from an HTML file, shaped like Markdown so the audit reads it the same way (design §4.1).

Headings become ``#`` lines, table rows become ``| a | b |`` lines, ``<pre>`` becomes a fenced code
block, and ``<script>``, ``<style>`` and ``<head>`` are dropped. Outside ``<pre>``, runs of whitespace
become one space, as a browser shows them.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

HEADINGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}
PARAGRAPHS = {"p", "div", "section", "article", "header", "footer", "nav", "ul", "ol", "table"}
LINES = {"li", "br"}
HIDDEN = {"script", "style", "head"}
FENCE = "```"
SPACES = re.compile(r"[ \t\r\n\f]+")
BLANK_LINES = re.compile(r"\n{3,}")


class _TextCollector(HTMLParser):
    """Collects text pieces in reading order; the HTMLParser API works only by subclassing (D-038)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.pieces: list[str] = []
        self.hidden_depth = 0
        self.in_pre = False
        self.row: list[str] | None = None

    # HTMLParser passes the tag's attributes; extracting text needs none of them.
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:  # noqa: ARG002
        if tag in HIDDEN:
            self.hidden_depth += 1
        elif tag in HEADINGS:
            self.pieces.append("\n\n" + "#" * HEADINGS[tag] + " ")
        elif tag == "pre":
            self.in_pre = True
            self.pieces.append(f"\n\n{FENCE}\n")
        elif tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.row.append("")
        elif tag in PARAGRAPHS or tag in LINES:
            self.pieces.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in HIDDEN:
            self.hidden_depth = max(0, self.hidden_depth - 1)
        elif tag in HEADINGS or tag in PARAGRAPHS:
            self.pieces.append("\n\n")
        elif tag == "pre" and self.in_pre:
            self.in_pre = False
            self.pieces[-1] = self.pieces[-1].removesuffix("\n")  # the newline before </pre> is not code
            self.pieces.append(f"\n{FENCE}\n\n")
        elif tag == "tr" and self.row is not None:
            cells = [cell.strip() for cell in self.row]
            self.pieces.append("| " + " | ".join(cells) + " |\n")
            self.row = None

    def handle_data(self, data: str) -> None:
        if self.hidden_depth:
            return
        if self.in_pre:
            opens_block = self.pieces[-1].endswith(f"{FENCE}\n") and data.startswith("\n")
            self.pieces.append(data[1:] if opens_block else data)
        elif self.row:
            self.row[-1] += SPACES.sub(" ", data)
        elif self.row is None:
            self.pieces.append(SPACES.sub(" ", data))


def _tidy(text: str) -> str:
    """Strip the spaces around each line outside code blocks, and keep at most one blank line."""
    lines: list[str] = []
    in_code = False
    for line in text.split("\n"):
        if line.strip() == FENCE:
            in_code = not in_code
        lines.append(line if in_code else line.strip())
    return BLANK_LINES.sub("\n\n", "\n".join(lines)).strip() + "\n"


def html_to_text(html: str) -> str:
    """The readable text of an HTML document, with Markdown-style headings, tables and code blocks."""
    collector = _TextCollector()
    collector.feed(html)
    collector.close()
    return _tidy("".join(collector.pieces))
