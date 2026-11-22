"""Finding chunk spans (design §4.2)."""

import pytest

from ragcourt import ChunkNotInSource, Document
from ragcourt.core.offsets import chunk_spans, find_text


def test_exact_then_whitespace_insensitive() -> None:
    assert find_text("a b\n c", "b\n c") == (2, 6)
    assert find_text("a b\n   c", "b c") == (2, 8)
    assert find_text("abc", "   ") is None
    assert find_text("abc", "x") is None


def test_overlapping_and_repeated_chunks_map_in_reading_order() -> None:
    document = Document("d.md", "ab ab ab")
    chunks = chunk_spans(document, ["ab", "ab ab", "ab"], "c")
    assert [(chunk.start, chunk.end) for chunk in chunks] == [(0, 2), (3, 8), (6, 8)]
    assert [chunk.index for chunk in chunks] == [0, 1, 2]


def test_a_whitespace_changed_chunk_keeps_the_source_text() -> None:
    document = Document("d.md", "one\ntwo   three")
    chunk = chunk_spans(document, ["one two three"], "c")[0]
    assert (chunk.start, chunk.end, chunk.text) == (0, 15, "one\ntwo   three")


def test_empty_pieces_are_dropped() -> None:
    chunks = chunk_spans(Document("d.md", "x y"), ["", "x", "  ", "y"], "c")
    assert [chunk.text for chunk in chunks] == ["x", "y"]


def test_a_chunk_not_in_the_source_names_chunker_document_index_and_text() -> None:
    with pytest.raises(ChunkNotInSource, match=r"Chunker 'mine' returned chunk 1 of 'd.md'.*'zzz'"):
        chunk_spans(Document("d.md", "abc"), ["abc", "zzz"], "mine")
