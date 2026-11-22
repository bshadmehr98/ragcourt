# Metrics, intervals and ties

A chunk is a **hit** when its span holds the whole gold quote. Per question, on the top results:

| Metric | Definition |
|---|---|
| `hit_at_k` | 1 if a hit is in the top k (k = 5 by default) |
| `mrr` | 1 / the rank of the first hit in the top 50, else 0 |
| `ndcg_at_k` | nDCG over the top k, a chunk's gain the share of the quote's tokens it holds |
| `recall_at_k` | the share of the quote's tokens covered by the top-k chunks |
| `token_precision_at_k` | quote tokens over all tokens in the top-k chunks (overlaps counted once) |
| `token_iou_at_k` | quote tokens covered over the union of quote tokens and top-k tokens |
| `recall_at_budget` | `recall_at_k` over chunks taken in rank order until 400 tokens (the default ranking metric) |

Tokens here are reference tokens (words and punctuation), the same for every embedder, so chunkers and
embedders compare fairly. `recall_at_budget` exists because without a budget the largest chunks always
win recall: a document returned whole holds every quote and buries it.

```python
from ragcourt.core.metrics import Ranking, all_metrics
from ragcourt.core.relevance import token_map
from ragcourt.types import Chunk
from ragcourt.types.questions import Question

text = "a b c d e f g h i j"
question = Question("q", "Q?", "keyword", "d.md", 4, 9, "c d e")
chunks = [Chunk("d.md", 0, 0, 5, "a b c"), Chunk("d.md", 1, 4, 11, "c d e f")]
metrics = all_metrics(Ranking(question, chunks, chunks, 2, 4), token_map({"d.md": text}))
assert metrics["mrr"] == 0.5 and metrics["recall_at_k"] == 1.0
assert round(metrics["recall_at_budget"], 2) == 0.67  # the budget of 4 tokens ends inside the answer
```

**Held-out only.** Pipelines are chosen on dev questions; every number in a leaderboard is from held-out
questions, so choosing does not inflate the result.

**Intervals.** Each mean comes with a 95% interval from 2,000 bootstrap resamples of the questions (fixed
seed). The overall score is the mean of the category means, so every category weighs the same.

**Ties.** The top two are compared on the same questions with a paired bootstrap of the difference. If its
interval contains 0, the output says **no significant difference**, marks every entry the top cannot be
told apart from with `=`, and names no winner. Each category also prints the **smallest difference** its
questions can tell apart: half the width of that interval. When another entry is separably better on one
category, the output says so ("On exact_term, … leads").

**Too few to rank.** A category with fewer than 30 held-out questions is shown with its count and left out
of the overall mean.
