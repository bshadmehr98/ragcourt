# 10. The metrics, one by one

A **metric** turns "the pipeline returned these chunks, in this order, for this question" into a number
between 0 and 1. ragcourt computes seven per question, then averages them (chapter 11). It ranks by one,
`recall_at_budget` unless you choose another with `--metric`.

Two words used below:
- A chunk is a **hit** when it holds the whole gold quote.
- **k** is how many chunks a language model would read (5 by default); **depth** is how far down the
  retrieved list ragcourt looks (50).

## A worked example

The document has ten tokens, `a b c d e f g h i j`. The gold quote is `c d e`. The pipeline returned two
chunks, in this order: chunk 1 = `a b c`, chunk 2 = `c d e f`. Take k = 2 and a budget of 4 tokens.

```python
from ragcourt.core.metrics import Ranking, all_metrics
from ragcourt.core.relevance import token_map
from ragcourt.types import Chunk
from ragcourt.types.questions import Question

text = "a b c d e f g h i j"
question = Question("q", "Q?", "keyword", "d.md", 4, 9, "c d e")
chunks = [Chunk("d.md", 0, 0, 5, "a b c"), Chunk("d.md", 1, 4, 11, "c d e f")]
m = all_metrics(Ranking(question, chunks, chunks, 2, 4), token_map({"d.md": text}))

assert m["hit_at_k"] == 1.0  # chunk 2 holds the whole quote and is in the top 2
assert m["mrr"] == 0.5  # the first hit is at rank 2: 1/2
assert m["recall_at_k"] == 1.0  # every quote token is somewhere in the top 2
assert round(m["token_precision_at_k"], 2) == 0.5  # 3 of the 6 distinct tokens returned are quote tokens
assert round(m["token_iou_at_k"], 2) == 0.5  # 3 shared / 6 in either
assert round(m["recall_at_budget"], 2) == 0.67  # 4 tokens read: a b c d; 2 of 3 quote tokens
```

## Each metric

**`hit_at_k`** (Hit@k): 1 if a hit is anywhere in the top k, else 0. The plainest question: "would the
language model have seen the answer?" Its average is the share of questions answered. It ignores where in
the top k the hit is, and gives nothing for a chunk with *most* of the quote.

**`mrr`** (mean reciprocal rank): 1 divided by the rank of the first hit, within the top 50; 0 if there is
none. Rank 1 gives 1, rank 2 gives 0.5, rank 10 gives 0.1. It rewards putting the answer *first*, which
matters when only the first chunk or two are read.

**`ndcg_at_k`** (normalized discounted cumulative gain): every chunk in the top k gets a **gain**, the
share of the quote's tokens it holds (so a half-answer counts half). Gains lower in the list are divided
by log₂(rank + 1), so rank 1 counts fully, rank 3 half. The total is divided by the best total possible
with this chunking, so 1 means "the best order this chunker allows". It rewards partial answers and good
order together.

**`recall_at_k`**: the share of the quote's tokens found anywhere in the top k chunks together. Gives
credit when the quote is split over two chunks that are both retrieved, which Hit@k does not.

**`token_precision_at_k`**: of all the text in the top k, the share that is quote. High precision means
little noise for the language model to read past. Large chunks score low.

**`token_iou_at_k`** (intersection over union): quote tokens found, divided by all tokens that are in the
quote *or* in the top k. 1 only when the top k is exactly the quote. Balances recall and precision.

**`recall_at_budget`** (the default): read the retrieved chunks in order until 400 tokens have been read
(the last chunk is cut at the budget), and count the share of the quote found. This is the fairest way to
compare **chunkers**: with Hit@k or recall@k, the biggest chunks always win (a whole document holds every
quote), but a language model's context is not free. With a fixed budget, a chunker wins only by putting
the answer in less text. Change the budget with `budget_tokens` (chapter 15).

## Which one should I rank by?

- Comparing chunkers or sizes: `recall_at_budget` (default).
- You always pass exactly k chunks to the model and only care whether the answer is there: `hit_at_k`.
- Only the first result matters (a search box, a "best answer"): `mrr`.
- Partial answers are useful to you: `ndcg_at_k` or `recall_at_k`.

Every metric is computed and saved for every pipeline whichever you rank by, so `results.json` has them
all. Tokens here are reference tokens (words and punctuation), the same for every embedder.

Next: [intervals and ties](11-statistics.md).
