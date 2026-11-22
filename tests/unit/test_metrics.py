"""Every metric against numbers worked out by hand (design §8.3, guarantee 10)."""

import pytest

from ragcourt.core.metrics import Ranking, all_metrics, first_hit
from ragcourt.core.relevance import is_hit, token_map
from ragcourt.types import Chunk
from ragcourt.types.questions import Question

# Ten one-letter words: tokens 0..9 at offsets 0, 2, 4, ... 18.
TEXT = "a b c d e f g h i j"
TOKENS = token_map({"d.md": TEXT})
QUOTE = Question("q", "Q?", "keyword", "d.md", 4, 9, "c d e")  # tokens 2, 3, 4


def chunk(index: int, start: int, end: int) -> Chunk:
    return Chunk("d.md", index, start, end, TEXT[start:end])


A = chunk(0, 0, 5)  # a b c      -> holds token 2 of the quote
B = chunk(1, 4, 11)  # c d e f    -> holds the whole quote: the hit
C = chunk(2, 12, 19)  # g h i j    -> nothing of the quote
ALL = [A, B, C]


def test_hits_and_first_hit() -> None:
    assert is_hit(B, QUOTE) and not is_hit(A, QUOTE)
    assert first_hit(Ranking(QUOTE, [A, C, B], ALL, 2, 400)) == 3


def test_hand_worked_values_hit_second() -> None:
    metrics = all_metrics(Ranking(QUOTE, [A, B, C], ALL, 2, 400), TOKENS)
    assert metrics["hit_at_k"] == 1.0
    assert metrics["mrr"] == 0.5
    # gains: A holds 1 of 3 quote tokens, B all 3; ideal order B, A.
    ideal = 1 + (1 / 3) / 1.584962500721156
    assert metrics["ndcg_at_k"] == pytest.approx((1 / 3 + 1 / 1.584962500721156) / ideal)
    assert metrics["recall_at_k"] == 1.0
    # top-2 spans cover tokens 0..5 (a b c d e f): 6 tokens, 3 of them the quote.
    assert metrics["token_precision_at_k"] == pytest.approx(3 / 6)
    assert metrics["token_iou_at_k"] == pytest.approx(3 / 6)


def test_hand_worked_values_with_a_budget() -> None:
    # Budget 4 tokens: A gives a b c (3), then B gives d (1 of its new tokens d e f): quote tokens c d.
    metrics = all_metrics(Ranking(QUOTE, [A, B, C], ALL, 2, 4), TOKENS)
    assert metrics["recall_at_budget"] == pytest.approx(2 / 3)


def test_a_miss_scores_zero() -> None:
    metrics = all_metrics(Ranking(QUOTE, [C, A], ALL, 1, 400), TOKENS)
    assert metrics["hit_at_k"] == metrics["mrr"] == metrics["recall_at_k"] == 0.0
    assert metrics["token_precision_at_k"] == 0.0 and metrics["ndcg_at_k"] == 0.0


def test_an_empty_quote_scores_zero() -> None:
    empty = Question("e", "Q?", "keyword", "d.md", 1, 1, "")
    metrics = all_metrics(Ranking(empty, [], ALL, 1, 400), TOKENS)
    assert set(metrics.values()) == {0.0}
