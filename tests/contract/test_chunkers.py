"""Every built-in chunker keeps its contract (design §7.1, add-stage step 3)."""

import pytest

from ragcourt import Document, load_documents, stages
from ragcourt.core.offsets import chunk_spans
from ragcourt.testing import corpus_path
from ragcourt.text_units import count_tokens

NATIVE = ["fixed", "markdown", "recursive", "sentence"]
DOCUMENTS = load_documents(corpus_path()).documents
EDGE_CASES = [
    "",
    "   \n\n ",
    "one line with no end",
    "x" * 5000,
    "Ünïcödé — ☃ text. Second sentence!\n\n" * 40,
]


@pytest.mark.parametrize("name", NATIVE)
def test_every_chunk_is_found_in_the_source_in_order(name: str) -> None:
    chunk = stages.find("chunker", name).function
    for document in DOCUMENTS:
        chunks = chunk_spans(document, chunk(document.text), name)
        assert chunks, document.id
        assert [c.start for c in chunks] == sorted(c.start for c in chunks)


@pytest.mark.parametrize("name", NATIVE)
@pytest.mark.parametrize("text", EDGE_CASES, ids=["empty", "blank", "one-line", "long-word", "unicode"])
def test_edge_cases(name: str, text: str) -> None:
    chunks = stages.find("chunker", name).function(text)
    chunk_spans(Document("d", text), chunks, name)
    assert all(piece.strip() for piece in chunks)
    assert chunks == stages.find("chunker", name).function(text)  # deterministic


@pytest.mark.parametrize("name", ["fixed", "markdown", "recursive"])
def test_sizes_are_kept(name: str) -> None:
    chunk = stages.find("chunker", name).function
    for document in DOCUMENTS:
        assert max(count_tokens(piece) for piece in chunk(document.text, size=80)) <= 80


def test_sentence_never_cuts_a_sentence() -> None:
    text = "A short one. " + "word " * 300 + "end. Last one."
    pieces = stages.find("chunker", "sentence").function(text, size=50)
    assert pieces[1].endswith("end.")


def test_overlap_repeats_the_end_of_the_previous_chunk() -> None:
    text = " ".join(f"w{n}" for n in range(100))
    first, second, *_ = stages.find("chunker", "fixed").function(text, size=20, overlap=5)
    assert first.split()[-5:] == second.split()[:5]
    sentences = " ".join(f"s{n} a b c." for n in range(30))
    recursive = stages.find("chunker", "recursive").function(sentences, size=20, overlap=6)
    assert recursive[1].startswith("s3 ") and recursive[0].endswith("s3 a b c.")
    assert max(len(piece.replace(".", " .").split()) for piece in recursive) <= 20


def test_markdown_starts_a_chunk_at_every_heading() -> None:
    text = "Intro.\n\n# One\n\nBody one.\n\nTwo\n===\n\nBody two."
    assert stages.find("chunker", "markdown").function(text) == [
        "Intro.",
        "# One\n\nBody one.",
        "Two\n===\n\nBody two.",
    ]
