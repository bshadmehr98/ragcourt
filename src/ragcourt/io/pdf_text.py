"""Reading a PDF as text, with the optional extra ``pdf`` (design §4.1, change 0005).

The text is what ``pypdf`` extracts, page by page, the pages joined by a blank line; nothing else is
changed (no words re-joined at line ends, no running header removed), so offsets are offsets into the text
ragcourt and every chunker were given. A PDF that cannot be read is skipped with its reason, never guessed.
Nothing inside a PDF is ever run or opened.
"""
# pyright: basic, reportMissingImports=false

from __future__ import annotations

import logging
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

MAX_PDF_BYTES = 50 * 2**20
MAX_PAGES = 5000
NEEDS_EXTRA = "install 'ragcourt[pdf]' to read PDF"


def extractor() -> str:
    """The extractor and its version, as outputs name it; "" without the extra."""
    try:
        return f"pypdf {version('pypdf')}"
    except PackageNotFoundError:
        return ""


def pdf_to_text(path: Path) -> tuple[str, str]:
    """The text of a PDF and "", or "" and the reason it is skipped."""
    try:
        import pypdf  # noqa: PLC0415 (an optional extra, imported only when used)
        from pypdf.errors import PyPdfError  # noqa: PLC0415
    except ImportError:
        return "", NEEDS_EXTRA
    if path.stat().st_size > MAX_PDF_BYTES:
        return "", f"PDF over {MAX_PDF_BYTES // 2**20} MB; split it or convert it to text"
    logging.getLogger("pypdf").setLevel(logging.ERROR)  # its warnings about a damaged file are our reason
    try:
        pages, reason = _pages(pypdf.PdfReader(path))
    # A damaged or hostile file can fail anywhere inside the parser; each failure is one skipped file.
    except (PyPdfError, ValueError, KeyError, TypeError, IndexError, OSError) as error:
        return "", f"damaged or not a PDF ({type(error).__name__}); convert it to text"
    text = "\n\n".join(page.strip() for page in pages if page.strip())
    if not reason and not text:
        reason = "no text in this PDF (scanned pages?): run OCR first"
    return ("", reason) if reason else (text.replace("\r\n", "\n").replace("\r", "\n"), "")


def _pages(reader: Any) -> tuple[list[str], str]:
    """Each page's text and "", or nothing and the reason the PDF is not read."""
    if reader.is_encrypted:
        return [], "encrypted PDF; remove its password first"
    if len(reader.pages) > MAX_PAGES:
        return [], f"PDF over {MAX_PAGES} pages; split it or convert it to text"
    return [page.extract_text() for page in reader.pages], ""
