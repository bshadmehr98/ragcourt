"""Reading PDF with the optional extra (design §4.1, change 0005)."""

import sys
from pathlib import Path

import pytest

from ragcourt import load_documents
from ragcourt.io.pdf_text import NEEDS_EXTRA, extractor, pdf_to_text
from tests.pdf_files import encrypted, pdf_bytes

PAGES = [["Larkspur keeps a dead job for 14 days.", "After that it is deleted (for good)."], ["Page two."]]


def test_pages_are_joined_by_a_blank_line_and_nothing_else_changes(tmp_path: Path) -> None:
    path = tmp_path / "manual.pdf"
    path.write_bytes(pdf_bytes(PAGES))
    text, reason = pdf_to_text(path)
    assert reason == ""
    assert text == "Larkspur keeps a dead job for 14 days.\nAfter that it is deleted (for good).\n\nPage two."
    assert extractor().startswith("pypdf ")


@pytest.mark.parametrize(
    ("data", "reason"),
    [
        (pdf_bytes([[], []]), "no text in this PDF (scanned pages?): run OCR first"),
        (encrypted(pdf_bytes(PAGES)), "encrypted PDF; remove its password first"),
        (pdf_bytes(PAGES)[:120], "damaged or not a PDF"),
        (b"just some words", "damaged or not a PDF"),
        (b"", "damaged or not a PDF"),
    ],
)
def test_a_pdf_that_cannot_be_read_gives_its_reason(tmp_path: Path, data: bytes, reason: str) -> None:
    path = tmp_path / "file.pdf"
    path.write_bytes(data)
    text, why = pdf_to_text(path)
    assert text == "" and why.startswith(reason)


def test_a_pdf_over_the_size_or_page_limit_is_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "big.pdf"
    path.write_bytes(pdf_bytes(PAGES))
    monkeypatch.setattr("ragcourt.io.pdf_text.MAX_PAGES", 1)
    assert pdf_to_text(path) == ("", "PDF over 1 pages; split it or convert it to text")
    monkeypatch.setattr("ragcourt.io.pdf_text.MAX_PDF_BYTES", 10)
    assert pdf_to_text(path)[1].startswith("PDF over 0 MB")


def test_without_the_extra_a_pdf_is_skipped_with_the_install_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "manual.pdf").write_bytes(pdf_bytes(PAGES))
    (tmp_path / "notes.md").write_text("# Notes\n\nKept.\n")
    monkeypatch.setitem(sys.modules, "pypdf", None)  # importing it now fails, as when it is not installed
    corpus = load_documents(tmp_path)
    assert [document.id for document in corpus.documents] == ["notes.md"]
    assert [(entry.path, entry.reason) for entry in corpus.skipped] == [("manual.pdf", NEEDS_EXTRA)]
    assert "ragcourt[pdf]" in NEEDS_EXTRA


def test_one_pdf_file_is_a_corpus(tmp_path: Path) -> None:
    path = tmp_path / "Manual.PDF"
    path.write_bytes(pdf_bytes(PAGES))
    corpus = load_documents(path)
    assert [document.id for document in corpus.documents] == ["Manual.PDF"]
