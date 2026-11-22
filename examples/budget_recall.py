"""Why size cannot win: recall within a token budget.

What: a "chunker" that returns each document whole finds every quote somewhere in its top k, yet gives a
reader far more text than the answer; ``recall_at_budget`` counts only the first 400 tokens retrieved.
How: two hand-made rankings of the same question, measured with ragcourt's metrics.
Why: without a budget, the biggest chunks always win recall (brief §5).
"""

from ragcourt.core.metrics import Ranking, all_metrics
from ragcourt.core.relevance import token_map
from ragcourt.types import Chunk
from ragcourt.types.questions import Question

text = "filler words " * 300 + "The first retry waits 10 seconds. " + "more filler " * 300
start = text.index("The first retry")
end = start + len("The first retry waits 10 seconds.")
quote = Question("q", "How long is the first retry?", "numeric", "d.md", start, end, text[start:end])
tokens = token_map({"d.md": text})
whole = [Chunk("d.md", 0, 0, len(text), text)]
small = [Chunk("d.md", 0, start - 20, start + 60, text[start - 20 : start + 60])]
for name, chunks in (("whole document", whole), ("small chunk", small)):
    metrics = all_metrics(Ranking(quote, chunks, chunks, 5, 400), tokens)
    print(f"{name:15s} recall_at_k={metrics['recall_at_k']:.2f}", end="  ")
    print(f"recall_at_budget={metrics['recall_at_budget']:.2f}")
assert all_metrics(Ranking(quote, whole, whole, 5, 400), tokens)["recall_at_budget"] < 1.0
