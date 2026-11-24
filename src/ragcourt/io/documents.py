"""Reading the user's documents (design §4.1, D-040).

Markdown, plain text, reStructuredText and HTML; PDF with the optional extra ``pdf`` (``io/pdf_text.py``).
Text files are read as UTF-8 (a byte-order
mark at the start is dropped); a file that is not valid UTF-8, or cannot be read, is skipped and reported,
never guessed. Line endings become ``\\n`` and nothing else in the text changes, so offsets are offsets
into what the user wrote (HTML is the exception: its readable text is extracted first). Hidden files and
folders, ``.ragcourt/`` among them, are left out. A link to a folder (or a broken link) is not followed but
reported, so no file is read twice; a link to a file is read like the file only when that file is inside
the folder (a link elsewhere, to a key file or `/proc`, is reported and skipped).
"""

from __future__ import annotations

from pathlib import Path

from ragcourt.errors import ConfigError
from ragcourt.io.html_text import html_to_text
from ragcourt.io.pdf_text import pdf_to_text
from ragcourt.types import Corpus, Document, Skipped

HTML_SUFFIXES = {".html", ".htm"}
MAX_HTML_BYTES = 5 * 2**20  # the standard parser can need 150 times a hostile file's size in memory
PDF_SUFFIX = ".pdf"  # read with the optional extra `pdf`; skipped with the reason without it
DOCUMENT_SUFFIXES = {".md", ".markdown", ".txt", ".rst", PDF_SUFFIX, *HTML_SUFFIXES}


def load_documents(path: Path) -> Corpus:
    """The documents under a folder (or one file), sorted by id, and the files skipped with a reason."""
    if path.is_file():
        return _load_one_file(path)
    if not path.is_dir():
        raise ConfigError(f"{path} does not exist. Give a folder of documents or one document.")
    files, skipped = _document_files(path)
    return _load_files(files, path, skipped)


def _load_one_file(path: Path) -> Corpus:
    if path.suffix.lower() not in DOCUMENT_SUFFIXES:
        readable = ", ".join(sorted(DOCUMENT_SUFFIXES))
        raise ConfigError(f"{path} is not a document ragcourt reads; it reads {readable}.")
    return _load_files([path], path.parent, [])


def _document_files(folder: Path) -> tuple[list[Path], list[Skipped]]:
    files: list[Path] = []
    skipped: list[Skipped] = []
    for path in folder.rglob("*"):
        relative = path.relative_to(folder)
        if any(part.startswith(".") for part in relative.parts):
            continue
        if path.is_symlink() and not path.is_file():
            reason = "a link to a folder or to nothing, not followed; give the folder itself"
            skipped.append(Skipped(relative.as_posix(), reason))
        elif path.is_symlink() and not path.resolve().is_relative_to(folder.resolve()):
            skipped.append(Skipped(relative.as_posix(), "a link to a file outside the folder, not followed"))
        elif path.is_file() and path.suffix.lower() in DOCUMENT_SUFFIXES:
            files.append(path)
    return files, skipped


def _load_files(files: list[Path], root: Path, skipped: list[Skipped]) -> Corpus:
    documents: list[Document] = []
    for path in files:
        document_id = path.relative_to(root).as_posix()
        text, reason = _read(path)
        if reason:
            skipped.append(Skipped(document_id, reason))
        else:
            documents.append(Document(id=document_id, text=text))
    documents.sort(key=lambda document: document.id)
    skipped.sort(key=lambda entry: entry.path)
    return Corpus(documents=tuple(documents), skipped=tuple(skipped))


def _read(path: Path) -> tuple[str, str]:
    """A file's text and "", or "" and the reason it is skipped."""
    suffix = path.suffix.lower()
    if suffix == PDF_SUFFIX:
        return pdf_to_text(path)
    if suffix in HTML_SUFFIXES and path.stat().st_size > MAX_HTML_BYTES:
        return "", f"HTML over {MAX_HTML_BYTES // 2**20} MB; convert it to text"
    try:
        raw = path.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError as error:
        return "", f"not valid UTF-8 (byte {error.start}); save it as UTF-8"
    except OSError as error:
        return "", f"cannot be read: {error.strerror or error}"
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    return (html_to_text(text) if suffix in HTML_SUFFIXES else text), ""
