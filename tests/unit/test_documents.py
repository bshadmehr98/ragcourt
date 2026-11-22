"""Loading documents (design §4.1)."""

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
