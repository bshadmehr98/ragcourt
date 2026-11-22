"""Blame: one miss, one cause, by arithmetic.

What: the stage and the mechanism that lost a question, with the evidence and whether a measurement
confirms it.
How: the same miss seen three ways: the quote alone would be found (diluted), keyword search finds it
(exact words), or nothing finds it (meaning).
Why: knowing why a question was missed tells you which stage to change (design §9).
"""

from dataclasses import replace

from ragcourt.core.blame import MEANINGS, cause
from ragcourt.core.blame.facts import Facts
from ragcourt.types import Chunk
from ragcourt.types.questions import Question

text = "intro " * 20 + "The answer is here, plainly stated. " + "tail " * 20
start = text.index("The answer")
question = Question("q", "Where is it?", "paraphrase", "d.md", start, start + 35, text[start : start + 35])
chunks = [Chunk("d.md", 0, 0, len(text), text), Chunk("d.md", 1, 0, 10, text[:10])]
missed = Facts(
    question,
    chunks,
    retrieved=(1,),
    final=(1,),
    k=1,
    retriever="dense",
    reranker="none",
    chunk_tokens=[60, 2],
    quote_tokens=7,
)
for probes in ({"quote_alone_reaches": True}, {"bm25_rank": 2}, {}):
    mechanism, evidence, _ = cause(replace(missed, **probes))  # type: ignore[arg-type]
    print(f"{mechanism:22s} {MEANINGS[mechanism]} ({evidence})")
