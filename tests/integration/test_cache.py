"""The embedding cache in plain files (design §10.2)."""

from pathlib import Path

import pytest

from ragcourt.io.cache import CachedEmbedder, EmbeddingStore, identity_of, text_key
from ragcourt.testing import FakeEmbedder


def cached(root: Path, embedder: FakeEmbedder | None = None) -> CachedEmbedder:
    inner = embedder or FakeEmbedder(dimensions=8)
    return CachedEmbedder(inner, EmbeddingStore.open(root, identity_of(inner)))


def test_a_second_run_embeds_nothing(tmp_path: Path) -> None:
    first = cached(tmp_path)
    result = first.embed(["a b", "c", "a b"])
    assert first.texts_embedded == 2 and first.calls == 1
    expected = FakeEmbedder(dimensions=8).embed(["a b", "c", "a b"])
    assert result.token_counts == expected.token_counts
    for got, want in zip(result.vectors, expected.vectors, strict=True):
        assert got == pytest.approx(want, abs=1e-6)  # stored as float32
    second = cached(tmp_path)
    assert second.embed(["c", "a b"]).vectors == [result.vectors[1], result.vectors[0]]
    assert second.calls == 0
    assert second.embed(["new"]).token_counts == [1]
    assert second.texts_embedded == 1


def test_questions_and_chunks_are_cached_apart(tmp_path: Path) -> None:
    store = cached(tmp_path)
    store.embed(["same"])
    store.embed(["same"], as_query=True)
    assert store.texts_embedded == 2
    assert text_key("same", as_query=True) != text_key("same", as_query=False)


def test_a_torn_last_write_is_trimmed(tmp_path: Path) -> None:
    store = cached(tmp_path)
    store.embed(["one", "two"])
    folder = store.store.folder
    with (folder / "vectors.f32").open("ab") as handle:
        handle.write(b"\0" * 32)  # a vector whose key was never written
    reloaded = cached(tmp_path)
    assert len(reloaded.store.vectors) == 2
    keys = (folder / "keys.txt").read_text().splitlines()
    assert len(keys) == 2 and keys[0].split(" ")[1].isdigit()


def test_another_identity_gets_another_folder(tmp_path: Path) -> None:
    small = cached(tmp_path, FakeEmbedder(dimensions=8))
    other = cached(tmp_path, FakeEmbedder(dimensions=8, max_tokens=3))
    assert small.store.folder != other.store.folder
    assert identity_of(FakeEmbedder()).startswith("fake-embedder|")
    assert (small.model, small.max_tokens, small.tokenizer) == (
        "fake-embedder",
        512,
        FakeEmbedder().tokenizer,
    )


def test_unknown_counts_stay_unknown(tmp_path: Path) -> None:
    class NoCounts(FakeEmbedder):
        def embed(self, texts: list[str], *, as_query: bool = False):  # type: ignore[override]
            vectors = super().embed(texts).vectors
            from ragcourt.types import Embedded

            return Embedded(vectors, None)

    store = cached(tmp_path, NoCounts(dimensions=4))
    assert store.embed(["x"]).token_counts is None
    assert cached(tmp_path, NoCounts(dimensions=4)).embed(["x"]).token_counts is None


def test_a_torn_write_never_shifts_later_vectors(tmp_path: Path) -> None:
    store = cached(tmp_path)
    store.embed(["one", "two"])
    folder = store.store.folder
    with (folder / "vectors.f32").open("ab") as handle:
        handle.write(b"\1" * 32 + b"\2" * 3)  # a whole orphan vector and a partial one
    again = cached(tmp_path)
    fresh = again.embed(["three"])
    reloaded = cached(tmp_path)
    assert reloaded.embed(["three"]).vectors == fresh.vectors and reloaded.calls == 0
    assert (folder / "vectors.f32").stat().st_size == 3 * 8 * 4
