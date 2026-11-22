# 12. Ranking pipelines: the search and the leaderboards

```text
ragcourt rank my_docs/
```

## The plan comes first

Before any model is called, `rank` prints:

- each **role** (writer, judge, embedders, reranker), its model, where that choice came from (built-in
  default, `ragcourt.toml`, or a flag), what it does and what it is shown;
- the **steps** and what each compares;
- an **estimate**: minutes (from speeds measured on your machine), texts to embed, reranking calls, and
  the money cost (local models cost nothing).

Then it asks "Start this run?". `--yes` skips the question.

## Why not try every combination?

Four chunkers × three embedders × three retrievers × two rerankers is 72 pipelines, each embedding all
your chunks and answering hundreds of questions. Instead ragcourt searches **greedily**, one stage at a
time, keeping the best so far:

| Step | Varies | Keeps fixed |
|---|---|---|
| 1. embedders | every embedder | the first chunker, `dense`, no reranker |
| 2. chunkers | every chunker | the best embedder, `dense`, no reranker |
| 3. retrievers | `dense`, `bm25`, `hybrid` | the best chunker and embedder |
| 4. rerankers | none and each reranker | the best of everything above |

That is 3 + 5 + 3 + 2 = 13 pipelines by default instead of 72. The cost: a combination that only shines
together (say a tiny chunker with one particular embedder) can be missed. Embedders go first because they
change everything else's numbers the most.

At each step the best is **chosen on dev** questions and the **leaderboard** shows held-out results
(chapter 11).

## Reading a leaderboard

```text
Leaderboard: chunkers (recall_at_budget, held-out)
   pipeline                                                     overall            paraphrase   …
   markdown:size=512,overlap=64 | embeddinggemma | dense | none    0.62 [0.50, 0.78]  …
=  recursive:size=256,overlap=32 | embeddinggemma | dense | none   0.55 [0.42, 0.65]  …
=  fixed:size=256,overlap=32 | embeddinggemma | dense | none       0.50 [0.33, 0.65]  …
   recursive:size=512,overlap=64 | embeddinggemma | dense | none   0.43 [0.31, 0.55]  …
No significant difference between markdown… and recursive…, fixed…: no winner.
distractor: too few to rank (5 held-out questions).
Smallest difference these questions can tell apart: …
Chosen for the next step (on dev questions): recursive:size=256,overlap=32 | …
```

- A **pipeline** is written `chunker | embedder | retriever | reranker` (`-` for no embedder: BM25 needs
  none).
- Each cell is the mean and its 95% interval; one column per kind of question.
- `=` marks entries tied with the top. The last one has no `=`: it is clearly worse.
- The chosen pipeline can differ from the top row: it was chosen on dev questions, the table shows
  held-out ones, and both are tied.

## After the four steps

- **Chosen pipeline**: your answer.
- **Ceilings** and **why questions were missed** (chapter 13).
- `.ragcourt/runs/<run-id>/results.json` with everything, and `report.html` with `--html` or
  `ragcourt report`.

## Choosing what to compare

```text
ragcourt rank my_docs/ --embedders nomic-embed-text,bge-m3
ragcourt rank my_docs/ --chunkers "markdown;sentence:size=200;recursive:size=1024,overlap=128"
ragcourt rank my_docs/ --retrievers dense,hybrid --rerankers llm
ragcourt rank my_docs/ --metric hit_at_k --k 3
ragcourt rank my_docs/ --questions 150          # more questions per kind: narrower intervals
```

Chunker specs carry commas, so they are separated by `;`. The same lists can live in `ragcourt.toml`
(chapter 15).

## How long it takes

Measured on an 8 GB GPU with the defaults (chapter 19): about 2 minutes for a dozen short pages with a few
questions per kind, about 70 minutes for 160 pages of documentation (FastAPI's) with the full 540
questions: 44 minutes writing questions, 4 minutes embedding, 20 minutes for the `llm` reranker. The plan
shows the estimate before anything starts. Later runs reuse the questions and the cached embeddings: the
FastAPI run again took about 22 minutes, nearly all of it the reranker; without `llm` in `--rerankers`, a
new chunker is measured in a minute or two.

Next: [why a question was missed](13-why-questions-fail.md).
