# Why a question was missed

For every held-out question the chosen pipeline misses, `ragcourt explain` gives one **cause**: a stage and
a mechanism, with the **evidence** (numbers from the run), an **evidence level** and a **fix**. It is
arithmetic on spans, ranks and a few extra measurements; no model is asked.

| Stage | Mechanism | Means |
|---|---|---|
| chunker | `too_small` | the quote is longer than any chunk |
| | `split` | the quote is cut across a chunk boundary |
| | `dropped` | part of the quote is in no chunk |
| | `over_limit` | the quote lies past the embedder's input limit inside its chunk: it was never read |
| | `diluted` | the quote alone would be found; inside its long or mixed chunk it is not |
| embedder | `exact_words` | keyword search finds it; the embedder blurs the exact words |
| | `distracted` | a similar passage that does not answer took its place |
| | `meaning` | the embedder does not connect the question to its answer |
| retriever | `keyword_only` | BM25 misses it; dense search finds it |
| | `fusion` | one half of the hybrid search finds it; the fused list does not |
| | `crowded` | near-duplicates fill the retrieved list |
| retrieval | `not_found` | only for [your own pipeline](stages.md#your-own-pipeline-measure-the-system-you-already-have): a chunk holds the quote and your system does not return it |
| ranking | `reranker_demoted` | the reranker pushed it out of the top k |
| | `distracted` | the misleading passage ranks above it |
| | `duplicates` | near-duplicates take the top k |
| | `not_rescued` | retrieved below k and nothing lifted it |

The checks run in this order; the first that holds is the cause and later ones are "also seen".

**The probes** tell causes apart: the quote embedded alone (diluted or meaning?), BM25's rank of the chunk
(exact words or meaning?), the quote's token position (over the limit?), every measured embedder's rank,
ranks before and after the reranker, near-duplicates from the audit, and a distractor's twin passage.

**Levels.** `confirmed`: a pipeline measured in this run that differs only in the blamed stage finds the
question; the fix names it. `indicated`: the probes point to the cause but no such pipeline was measured;
the fix says "not measured" and how to measure it. The share of confirmed blames is printed. For
[your own pipeline](stages.md#your-own-pipeline-measure-the-system-you-already-have) `confirmed` means
less: a pipeline ragcourt measured in the same run finds the question, which shows it can be found on your
documents, not which stage of your system lost it.

**Ceilings** show what each stage costs: the share of questions with an intact chunk (chunker), retrieved
(retrieval), and in the top k (hit@k). They cannot increase; each gap is the share lost to that stage.

`ragcourt explain --show ID` prints the quote (between « and ») in its text with the chunk boundaries.

```python
from dataclasses import replace

from ragcourt.core.blame import cause
from ragcourt.core.blame.facts import Facts
from ragcourt.types import Chunk
from ragcourt.types.questions import Question

text = "intro " * 20 + "The answer is here, plainly stated. " + "tail " * 20
start = text.index("The answer")
question = Question("q", "Where?", "paraphrase", "d.md", start, start + 35, text[start : start + 35])
chunks = [Chunk("d.md", 0, 0, len(text), text), Chunk("d.md", 1, 0, 10, text[:10])]
missed = Facts(question, chunks, (1,), (1,), 1, "dense", "none", [60, 2], 7)
assert cause(replace(missed, quote_alone_reaches=True))[0] == "chunker.diluted"
assert cause(replace(missed, bm25_rank=2))[0] == "embedder.exact_words"
```
