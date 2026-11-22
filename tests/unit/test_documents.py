"""Loading documents (design §4.1)."""

import os
from pathlib import Path

import pytest

from ragcourt import ConfigError, load_documents


def write(path: Path, text: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(text, bytes):
        path.write_bytes(text)
    else:
        path.write_text(text, encoding="utf-8")


def test_text_formats_are_loaded_sorted_by_posix_id(tmp_path: Path) -> None:
    for name in ("b.md", "a.txt", "sub/c.rst", "sub/d.markdown", "e.htm", "f.html"):
        write(tmp_path / name, f"<p>{name}</p>" if "htm" in name else name)
    corpus = load_documents(tmp_path)
    ids = [document.id for document in corpus.documents]
    assert ids == ["a.txt", "b.md", "e.htm", "f.html", "sub/c.rst", "sub/d.markdown"]
    assert corpus.documents[2].text == "e.htm\n"
    assert corpus.skipped == ()


def test_other_files_and_hidden_paths_are_skipped_silently(tmp_path: Path) -> None:
    write(tmp_path / "doc.md", "kept")
    write(tmp_path / "notes.pdf", b"%PDF")
    write(tmp_path / "script.py", "x = 1")
    write(tmp_path / ".hidden.md", "no")
    write(tmp_path / ".ragcourt" / "cache.md", "no")
    write(tmp_path / ".git" / "README.md", "no")
    corpus = load_documents(tmp_path)
    assert [document.id for document in corpus.documents] == ["doc.md"]


def test_line_endings_are_normalised_and_nothing_else_changes(tmp_path: Path) -> None:
    write(tmp_path / "doc.md", b"  one\r\ntwo\rthree\t \n")
    assert load_documents(tmp_path).documents[0].text == "  one\ntwo\nthree\t \n"


def test_a_file_that_is_not_utf8_is_skipped_with_its_reason(tmp_path: Path) -> None:
    write(tmp_path / "good.md", "fine")
    write(tmp_path / "latin.txt", "café".encode("latin-1"))
    corpus = load_documents(tmp_path)
    assert [document.id for document in corpus.documents] == ["good.md"]
    assert corpus.skipped[0].path == "latin.txt"
    assert "not valid UTF-8" in corpus.skipped[0].reason


def test_one_file_can_be_loaded_alone(tmp_path: Path) -> None:
    write(tmp_path / "one.md", "alone")
    corpus = load_documents(tmp_path / "one.md")
    assert [(document.id, document.text) for document in corpus.documents] == [("one.md", "alone")]


def test_a_missing_path_says_what_to_give(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="does not exist"):
        load_documents(tmp_path / "nowhere")


def test_a_byte_order_mark_is_dropped(tmp_path: Path) -> None:
    write(tmp_path / "bom.md", "﻿# Title\n".encode())
    assert load_documents(tmp_path).documents[0].text == "# Title\n"


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads every file")
def test_an_unreadable_file_is_skipped_with_its_reason(tmp_path: Path) -> None:
    write(tmp_path / "ok.md", "fine")
    write(tmp_path / "locked.md", "secret")
    (tmp_path / "locked.md").chmod(0)
    try:
        corpus = load_documents(tmp_path)
    finally:
        (tmp_path / "locked.md").chmod(0o600)
    assert [document.id for document in corpus.documents] == ["ok.md"]
    assert corpus.skipped[0].path == "locked.md"
    assert corpus.skipped[0].reason.startswith("cannot be read")


def test_one_file_of_another_kind_is_refused(tmp_path: Path) -> None:
    write(tmp_path / "paper.pdf", b"%PDF-1.7")
    with pytest.raises(
        ConfigError, match=r"not a document ragcourt reads; it reads \.htm, \.html, \.markdown"
    ):
        load_documents(tmp_path / "paper.pdf")


def test_links_to_files_are_read_and_links_to_folders_reported(tmp_path: Path) -> None:
    write(tmp_path / "elsewhere" / "inner.md", "inner")
    write(tmp_path / "docs" / "real.md", "real")
    (tmp_path / "docs" / "linked.md").symlink_to(tmp_path / "docs" / "real.md")
    (tmp_path / "docs" / "folder").symlink_to(tmp_path / "elsewhere", target_is_directory=True)
    (tmp_path / "docs" / "broken.md").symlink_to(tmp_path / "missing.md")
    corpus = load_documents(tmp_path / "docs")
    assert [document.id for document in corpus.documents] == ["linked.md", "real.md"]
    assert [entry.path for entry in corpus.skipped] == ["broken.md", "folder"]


def test_suffixes_ignore_case_nested_hidden_folders_are_left_out_and_empty_files_kept(tmp_path: Path) -> None:
    write(tmp_path / "UPPER.MD", "upper")
    write(tmp_path / "a" / ".cache" / "b" / "deep.md", "hidden")
    write(tmp_path / "empty.txt", "")
    corpus = load_documents(tmp_path)
    assert [(document.id, document.text) for document in corpus.documents] == [
        ("UPPER.MD", "upper"),
        ("empty.txt", ""),
    ]


def test_a_link_out_of_the_folder_is_skipped_and_huge_html_too(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ragcourt.io import documents

    secret = tmp_path / "secret.txt"
    secret.write_text("sk-live-key")
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "real.md").write_text("A real document.")
    (docs / "inside.md").symlink_to(docs / "real.md")
    (docs / "env.txt").symlink_to(secret)
    monkeypatch.setattr(documents, "MAX_HTML_BYTES", 10)
    (docs / "page.html").write_text("<p>" + "x" * 50 + "</p>")
    corpus = load_documents(docs)
    assert [d.id for d in corpus.documents] == ["inside.md", "real.md"]
    reasons = {entry.path: entry.reason for entry in corpus.skipped}
    assert reasons["env.txt"] == "a link to a file outside the folder, not followed"
    assert reasons["page.html"].startswith("HTML over")
