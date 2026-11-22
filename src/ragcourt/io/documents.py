"""Reading the user's documents (design §4.1).

Text formats only: Markdown, plain text, reStructuredText and HTML. Files are read as UTF-8; a file that
is not valid UTF-8 is skipped and reported, never guessed. Line endings become ``\\n`` and nothing else in
the text changes, so offsets are offsets into what the user wrote (HTML is the exception: its readable
text is extracted first). Hidden files and folders, ``.ragcourt/`` among them, are skipped.
"""

from __future__ import annotations

from pathlib import Path

from ragcourt.errors import ConfigError
from ragcourt.io.html_text import html_to_text
from ragcourt.types import Corpus, Document, Skipped

TEXT_SUFFIXES = {".md", ".markdown", ".txt", ".rst"}
HTML_SUFFIXES = {".html", ".htm"}


def load_documents(path: Path) -> Corpus:
    """The documents under a folder (or one file), sorted by id, and the files skipped with a reason."""
    if path.is_file():
        return _load_files([path], path.parent)
    if not path.is_dir():
        raise ConfigError(f"{path} does not exist. Give a folder of documents or one document.")
    return _load_files(_document_files(path), path)


def _document_files(folder: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(folder.rglob("*")):
        relative = path.relative_to(folder)
        hidden = any(part.startswith(".") for part in relative.parts)
        if path.is_file() and not hidden and path.suffix.lower() in TEXT_SUFFIXES | HTML_SUFFIXES:
            files.append(path)
    return files


def _load_files(files: list[Path], root: Path) -> Corpus:
    documents: list[Document] = []
    skipped: list[Skipped] = []
    for path in files:
        document_id = path.relative_to(root).as_posix()
        try:
            raw = path.read_bytes().decode("utf-8")
        except UnicodeDecodeError as error:
            skipped.append(Skipped(document_id, f"not valid UTF-8 (byte {error.start}); save it as UTF-8"))
            continue
        documents.append(Document(id=document_id, text=_text_of(path, raw)))
    documents.sort(key=lambda document: document.id)
    return Corpus(documents=tuple(documents), skipped=tuple(skipped))


def _text_of(path: Path, raw: str) -> str:
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    if path.suffix.lower() in HTML_SUFFIXES:
        return html_to_text(text)
    return text
