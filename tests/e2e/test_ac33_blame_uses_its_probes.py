"""Guarantee 33: blame uses its probes (design §9.4, §16).

``chunker.diluted`` is told from ``embedder.meaning`` by the quote-alone probe, ``embedder.exact_words`` from
``embedder.meaning`` by the keyword rank, and ``chunker.over_limit`` by the quote's token position.
"""

from dataclasses import replace

from ragcourt.core.blame import cause
from ragcourt.core.blame.facts import Facts
from ragcourt.types import Chunk
from ragcourt.types.questions import Question

TEXT = "intro " * 20 + "The answer is here, plainly stated. " + "tail " * 20
START = TEXT.index("The answer")
END = START + len("The answer is here, plainly stated.")
QUESTION = Question("q", "Where?", "paraphrase", "d.md", START, END, TEXT[START:END], "held-out")
CHUNKS = [Chunk("d.md", 0, 0, len(TEXT), TEXT), Chunk("d.md", 1, 0, 10, TEXT[:10])]
LOST = Facts(
    QUESTION,
    CHUNKS,
    retrieved=(1,),
    final=(1,),
    k=1,
    retriever="dense",
    reranker="none",
    chunk_tokens=[60, 2],
    quote_tokens=7,
)


def test_the_quote_alone_tells_diluted_from_meaning() -> None:
    assert cause(replace(LOST, quote_alone_reaches=True))[0] == "chunker.diluted"
    assert cause(replace(LOST, quote_alone_reaches=False))[0] == "embedder.meaning"


def test_the_keyword_rank_tells_exact_words_from_meaning() -> None:
    assert cause(replace(LOST, quote_alone_reaches=False, bm25_rank=2))[0] == "embedder.exact_words"
    assert cause(replace(LOST, quote_alone_reaches=False, bm25_rank=None))[0] == "embedder.meaning"


def test_the_token_position_finds_over_limit() -> None:
    assert cause(replace(LOST, limit=40, quote_end_tokens=48))[0] == "chunker.over_limit"
    assert (
        cause(replace(LOST, limit=40, quote_end_tokens=30, quote_alone_reaches=False))[0]
        == "embedder.meaning"
    )
