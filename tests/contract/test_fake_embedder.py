"""The fake embedder behaves like an embedder (design §7.1, §15.2)."""

import math
import subprocess
import sys

from ragcourt.testing import FakeEmbedder, fake_tokens
from ragcourt.types import Embedder


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def test_it_implements_the_embedder_protocol() -> None:
    embedder: Embedder = FakeEmbedder()
    assert embedder.model == "fake-embedder"
    assert embedder.max_tokens == 512
    assert embedder.tokenizer


def test_vectors_are_unit_length_sized_and_come_with_token_counts() -> None:
    embedded = FakeEmbedder().embed(["Retries wait ten seconds.", "Timeouts stop running jobs."])
    assert [len(vector) for vector in embedded.vectors] == [256, 256]
    assert embedded.token_counts == [5, 5]
    for vector in embedded.vectors:
        assert math.isclose(math.sqrt(sum(value * value for value in vector)), 1.0)


def test_a_vector_is_the_same_on_every_machine_and_in_every_process() -> None:
    # Worked out once and pinned: a change of hash function or features changes it.
    golden = [0.0, -0.5, 0.0, -0.5, 0.0, 0.0, -0.5, -0.5]
    assert FakeEmbedder(dimensions=8).embed(["retry later please"]).vectors[0] == golden
    code = "from ragcourt.testing import FakeEmbedder; print(FakeEmbedder(dimensions=8).embed(['retry later please']).vectors[0])"
    for seed in ("1", "2"):
        out = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            check=True,
            env={"PYTHONHASHSEED": seed},
        )
        assert out.stdout.strip() == str(golden)


def test_word_order_counts_through_word_pairs() -> None:
    forward, backward = FakeEmbedder().embed(["jobs retry later", "later retry jobs"]).vectors
    assert forward != backward
    assert cosine(forward, backward) > 0.5


def test_similar_texts_are_closer_than_unrelated_ones() -> None:
    query, near, far = (
        FakeEmbedder()
        .embed(
            [
                "how long do retries wait",
                "retries wait ten seconds before the next attempt",
                "the dashboard has no login",
            ]
        )
        .vectors
    )
    assert cosine(query, near) > cosine(query, far)


def test_text_past_the_limit_is_not_read_but_is_counted() -> None:
    embedded = FakeEmbedder(max_tokens=3).embed(["one two three", "one two three four five"])
    assert embedded.vectors[0] == embedded.vectors[1]
    assert embedded.token_counts == [3, 5]


def test_an_empty_text_is_a_zero_vector() -> None:
    assert FakeEmbedder(dimensions=4).embed([""]).vectors == [[0.0, 0.0, 0.0, 0.0]]


def test_tokens_are_words_and_punctuation() -> None:
    assert fake_tokens("Wait 10 s, then retry.") == ["wait", "10", "s", ",", "then", "retry", "."]


def test_questions_and_chunks_embed_alike_in_the_fake() -> None:
    embedder = FakeEmbedder()
    assert embedder.embed(["how long"], as_query=True) == embedder.embed(["how long"])
