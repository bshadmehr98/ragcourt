# 13. Why a question was missed

Knowing that a pipeline scores 0.62 does not tell you what to change. For every held-out question the
chosen pipeline misses, ragcourt names **one cause**: a stage and a mechanism, with the evidence and a fix.

```text
ragcourt explain                      # every miss
ragcourt explain --show 9468d50b1a4b  # one question: the quote among the chunk cuts
```

```text
9468d50b1a4b [exact_term] What does the documentation say about --drain-timeout?
  quote (timeouts.md): `--drain-timeout` option, 30 seconds by default, sets how long it waits.
  cause: chunker.split, indicated
  evidence: a chunk ends inside the quote: …'`--drain-timeout' | '` option, 30 seconds by defaul'…
  fix: a chunker that keeps this passage whole (not measured: `ragcourt rank DOCS --chunkers …` would measure it)
```

**No model decides the cause.** It is arithmetic on positions, ranks and a few extra measurements.

## The fifteen causes

They are checked in this order; the first that holds is the cause, any later one is printed as "also
seen".

**The chunker lost it**

| Cause | What happened | Typical fix |
|---|---|---|
| `chunker.too_small` | the quote is longer than any chunk | larger chunks |
| `chunker.split` | a chunk boundary cuts through the quote | a structure-aware chunker, overlap |
| `chunker.dropped` | part of the quote is in no chunk at all (the chunker skipped text) | a chunker that keeps all text |
| `chunker.over_limit` | the quote sits past the embedder's input limit inside its chunk: it was never read | smaller chunks, or an embedder with a longer limit |
| `chunker.diluted` | the quote *alone* would be found, but inside its long or mixed chunk it is not | smaller or more focused chunks |

**The embedder lost it**

| Cause | What happened | Typical fix |
|---|---|---|
| `embedder.exact_words` | keyword search (BM25) finds the chunk; the embedder does not | `hybrid` or `bm25` |
| `embedder.distracted` | a similar passage that does not answer took its place | another embedder, a reranker |
| `embedder.meaning` | neither the chunk nor the quote alone is found, and keywords don't help | another embedder |

**The retriever lost it**

| Cause | What happened | Typical fix |
|---|---|---|
| `retriever.keyword_only` | BM25 misses it, dense search finds it | `dense` or `hybrid` |
| `retriever.fusion` | one half of hybrid finds it, the merged list does not | other hybrid weights, or one half alone |
| `retriever.crowded` | near-duplicate chunks fill the retrieved list | remove duplicates |

**The ranking lost it** (it was retrieved, but not in the top k)

| Cause | What happened | Typical fix |
|---|---|---|
| `ranking.reranker_demoted` | it was in the top k before the reranker, not after | no reranker, or another one |
| `ranking.distracted` | the look-alike passage ranks above it | a reranker |
| `ranking.duplicates` | near-duplicates take the top k | remove duplicates |
| `ranking.not_rescued` | retrieved below k, and nothing lifted it | a reranker, or a larger k |

## The probes: how causes are told apart

To separate "the chunk is too long" from "the embedder doesn't understand", ragcourt measures a few more
things for each miss:

- the **quote embedded alone**: is it found when it isn't surrounded by other text? (diluted vs meaning)
- the chunk's **rank with BM25**: do the exact words find it? (exact words vs meaning)
- the quote's **position in tokens** inside its chunk: past the embedder's limit? (over limit)
- the chunk's rank with **every embedder** measured in step 1
- ranks **before and after the reranker**
- **near-duplicates** from the audit, and for distractor questions the **look-alike passage's** rank

## Confirmed or indicated

- **confirmed**: a pipeline measured in this same run that differs *only* in the blamed stage finds the
  question. The fix names it: "retriever dense finds it (measured in this run)". This is as close to proof
  as a measurement gets.
- **indicated**: the probes point to the cause, but no such pipeline was measured. The fix says "not
  measured" and gives the command that would measure it, or "measured here and not finding it either"
  when the alternatives tried did not help.

The share of confirmed causes is printed. More candidates per step means more confirmed causes.

## Ceilings: what each stage costs

```text
group       questions  chunker  retrieval  hit@k
overall            45     1.00       0.96   0.82
paraphrase          8     1.00       0.75   0.13
```

Read left to right, for the chosen pipeline:
- **chunker**: share of questions whose answer is whole in some chunk (no chunker cause).
- **retrieval**: share also retrieved within depth 50 (no embedder or retriever cause).
- **hit@k**: share that made the top k.

Each column can only go down. The biggest drop shows the stage to work on: above, the chunker loses
nothing, retrieval loses 4%, and ranking loses 14%, so a reranker is the thing to try. On paraphrase
questions retrieval already loses a quarter: an embedder problem.

Next: [every command](14-commands.md).
