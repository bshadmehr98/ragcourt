"""Every metric of design §8.3, for one question and one ranked list of chunks.

Averages, intervals and ties are in ``core/stats.py``; this module is per question, so every value can be
checked against a hand-worked fixture (guarantee 10).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ragcourt.core.relevance import TokenMap, is_hit
from ragcourt.types import Chunk
from ragcourt.types.questions import Question


@dataclass(frozen=True)
class Ranking:
    """What a metric needs: the question, the chunks in rank order, every chunk of the chunking, k, budget."""

    question: Question
    ranked: list[Chunk]
    all_chunks: list[Chunk]
    k: int
    budget_tokens: int


def first_hit(ranking: Ranking) -> int | None:
    """The 1-based rank of the first hit, or None."""
    for rank, chunk in enumerate(ranking.ranked, start=1):
        if is_hit(chunk, ranking.question):
            return rank
    return None


def hit_at_k(ranking: Ranking, tokens: TokenMap) -> float:  # noqa: ARG001 (every metric has this signature)
    """1 when a hit is in the top k."""
    rank = first_hit(ranking)
    return 1.0 if rank is not None and rank <= ranking.k else 0.0


def mrr(ranking: Ranking, tokens: TokenMap) -> float:  # noqa: ARG001
    """1 / the rank of the first hit in the top ``depth``, else 0."""
    rank = first_hit(ranking)
    return 1.0 / rank if rank else 0.0


def _quote_tokens(ranking: Ranking, tokens: TokenMap) -> set[tuple[str, int]]:
    question = ranking.question
    return tokens.tokens_in(question.document, question.start, question.end)


def _relevance(chunk: Chunk, quote: set[tuple[str, int]], tokens: TokenMap) -> float:
    if not quote:
        return 0.0
    return len(tokens.tokens_in(chunk.document, chunk.start, chunk.end) & quote) / len(quote)


def ndcg_at_k(ranking: Ranking, tokens: TokenMap) -> float:
    """nDCG over the top k with graded relevance; the ideal is the best k chunks of this chunking."""
    quote = _quote_tokens(ranking, tokens)
    gains = [_relevance(chunk, quote, tokens) for chunk in ranking.ranked[: ranking.k]]
    candidates = [chunk for chunk in ranking.all_chunks if chunk.document == ranking.question.document]
    ideal = sorted((_relevance(chunk, quote, tokens) for chunk in candidates), reverse=True)[: ranking.k]
    best = _dcg(ideal)
    return _dcg(gains) / best if best else 0.0


def _dcg(gains: list[float]) -> float:
    return sum(gain / math.log2(rank + 1) for rank, gain in enumerate(gains, start=1))


def _covered(chunks: list[Chunk], tokens: TokenMap) -> set[tuple[str, int]]:
    found: set[tuple[str, int]] = set()
    for chunk in chunks:
        found |= tokens.tokens_in(chunk.document, chunk.start, chunk.end)
    return found


def recall_at_k(ranking: Ranking, tokens: TokenMap) -> float:
    """The share of the quote's tokens covered by the union of the top-k spans."""
    quote = _quote_tokens(ranking, tokens)
    covered = _covered(ranking.ranked[: ranking.k], tokens)
    return len(quote & covered) / len(quote) if quote else 0.0


def token_precision_at_k(ranking: Ranking, tokens: TokenMap) -> float:
    """Quote tokens in the top-k spans over all tokens in them (overlaps counted once)."""
    quote = _quote_tokens(ranking, tokens)
    covered = _covered(ranking.ranked[: ranking.k], tokens)
    return len(quote & covered) / len(covered) if covered else 0.0


def token_iou_at_k(ranking: Ranking, tokens: TokenMap) -> float:
    """Quote tokens covered over the union of quote tokens and the top-k spans' tokens."""
    quote = _quote_tokens(ranking, tokens)
    covered = _covered(ranking.ranked[: ranking.k], tokens)
    union = quote | covered
    return len(quote & covered) / len(union) if union else 0.0


def recall_at_budget(ranking: Ranking, tokens: TokenMap) -> float:
    """Recall over chunks taken in rank order until the token budget; the last chunk is cut at it."""
    quote = _quote_tokens(ranking, tokens)
    taken: set[tuple[str, int]] = set()
    left = ranking.budget_tokens
    for chunk in ranking.ranked:
        if left <= 0:
            break
        inside = sorted(tokens.tokens_in(chunk.document, chunk.start, chunk.end) - taken)
        taken |= set(inside[:left])
        left -= min(left, len(inside))
    return len(quote & taken) / len(quote) if quote else 0.0


METRIC_FUNCTIONS = {
    "hit_at_k": hit_at_k,
    "mrr": mrr,
    "ndcg_at_k": ndcg_at_k,
    "recall_at_k": recall_at_k,
    "token_precision_at_k": token_precision_at_k,
    "token_iou_at_k": token_iou_at_k,
    "recall_at_budget": recall_at_budget,
}


def all_metrics(ranking: Ranking, tokens: TokenMap) -> dict[str, float]:
    """Every metric for one question."""
    return {name: function(ranking, tokens) for name, function in METRIC_FUNCTIONS.items()}
