"""The fake embedder behaves like an embedder (design §7.1, §15.2)."""

import math

from ragcourt.testing import FakeEmbedder, fake_tokens
from ragcourt.types import Embedder


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def test_it_implements_the_embedder_protocol() -> None:
    embedder: Embedder = FakeEmbedder()
    assert embedder.model == "fake-embedder"
    assert embedder.max_tokens == 512
    assert embedder.tokenizer


def test_vectors_are_deterministic_unit_length_and_sized() -> None:
    texts = ["Retries wait ten seconds.", "Timeouts stop running jobs."]
    first = FakeEmbedder().embed(texts)
    assert first == FakeEmbedder().embed(texts)
    assert [len(vector) for vector in first] == [256, 256]
    for vector in first:
        assert math.isclose(math.sqrt(sum(value * value for value in vector)), 1.0)


def test_similar_texts_are_closer_than_unrelated_ones() -> None:
    query, near, far = FakeEmbedder().embed(
        [
            "how long do retries wait",
            "retries wait ten seconds before the next attempt",
            "the dashboard has no login",
        ]
    )
    assert cosine(query, near) > cosine(query, far)


def test_text_past_the_limit_is_not_read() -> None:
    embedder = FakeEmbedder(max_tokens=3)
    same = embedder.embed(["one two three", "one two three four five"])
    assert same[0] == same[1]


def test_an_empty_text_is_a_zero_vector() -> None:
    assert FakeEmbedder(dimensions=4).embed([""]) == [[0.0, 0.0, 0.0, 0.0]]


def test_tokens_are_words_and_punctuation() -> None:
    assert fake_tokens("Wait 10 s, then retry.") == ["wait", "10", "s", ",", "then", "retry", "."]
    assert FakeEmbedder().count_tokens(["a b.", ""]) == [3, 0]
