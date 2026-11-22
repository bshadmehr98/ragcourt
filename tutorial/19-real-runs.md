# 19. Real runs: what we tested and what we saw

Everything in this chapter was run on the maintainer's laptop in November 2026, with real local models:
an Intel i9-14900HX, 30 GB of RAM, an NVIDIA RTX 4060 with 8 GB, Ollama 0.34.4. The scripts and full
notes are in [design/history/](../design/history/). Your numbers will differ: that is the point of
measuring on your own documents.

## 1. Choosing the default models

Before writing ragcourt, we measured which local models could do the work
([0002](../design/history/0002-local-models.md)).

**Embedders**, on 134 chunks of developer documentation:

| Model | Texts per second | Vector size | Advertised input limit |
|---|---|---|---|
| `all-minilm` | 125 | 384 | 512 |
| `nomic-embed-text` | 107 | 768 | 2,048 |
| `mxbai-embed-large` | 59 | 1,024 | 512 |
| `embeddinggemma` | 51 | 768 | 2,048 |
| `bge-m3` | 44 | 1,024 | 8,192 |
| `qwen3-embedding:0.6b` | 8 | 1,024 | 32,768 |

**Chat models** writing 20 questions each with an exact quote: `gemma4` 19 of 20 quotes found in the text,
`qwen3:4b` 14, `llama3.2:3b` 13 of 17, `qwen3:1.7b` 7 of 21. All of them sometimes wrote bare identifiers
as "questions" and lines of code as "quotes", which is why the code rules of chapter 8 exist.

**Judges**: with a plain prompt, `gemma4` graded "I need more context" as a correct answer. Smaller models
graded `UNKNOWN` as correct again and again. This is why the judge got a strict prompt and must pass a
40-case self-test before it is used (chapter 9). With the final prompts, `gemma4` scores 98%.

**Lesson**: `gemma4` plus three fast embedders fit together in 8 GB, so they became the defaults.

## 2. Can a local model write each kind of question?

Asked for one question of each kind on 8 paragraphs, `gemma4` got the quote right almost always but the
*kind* often wrong ([0003](../design/history/0003-question-categories.md)):

| Kind | Really of that kind |
|---|---|
| paraphrase | 7 of 8 |
| keyword | 7 of 8 |
| exact_term | 3 of 8 |
| numeric | 3 of 8 |
| distractor | 2 of 8 |
| negation | 1 of 8 |

Asked for a negation about a passage with no negation, it invented one. Counted as "hard questions", these
would have blamed embedders for the writer's mistakes. **Lesson**: choose by code which passages can
support each kind, and check every question's kind by code and by the judge.

## 3. Reading real documents

We loaded seven real corpora ([0004](../design/history/0004-real-data.md)): the Kubernetes concepts docs
(191 Markdown files), CPython's library docs (359 reStructuredText files), FastAPI's docs, Python docs and
Wikipedia pages as HTML, Chroma's chunking benchmark and MultiHop-RAG's 609 news articles. Text files came
through byte for byte. **HTML was the weak part**: a Python docs page started with 40 lines of menus, a
Wikipedia page with 90. ragcourt now keeps the page's main content and drops navigation.

## 4. Ollama reads less than models advertise

Measured with an over-long text:

| Model | Advertised | Read by default | Read when asked for the full length |
|---|---|---|---|
| `nomic-embed-text` | 2,048 | 2,048 | 2,048 |
| `mxbai-embed-large` | 512 | 512 | 512 |
| `embeddinggemma` | 2,048 | 2,048 | 2,048 |
| `bge-m3` | 8,192 | **2,048** | 8,192 |
| `all-minilm` | 512 | **256** | 512 |

Ollama cuts the rest silently. A chunker ranked with `bge-m3` at 8,192 tokens would have been read only to
2,048, with no warning. **Lesson**: ragcourt asks for the full length and measures the limit in force
(chapter 5).

## 5. How often does naive chunking cut the answer?

On Chroma's chunking benchmark (questions written by GPT-4, with exact gold spans), 800-character chunks
cut **about one gold quote in five** before any embedder was involved: 14 of 76 on State of the Union, 28
of 144 on WikiTexts. And the best embedder changed with the corpus (mxbai ahead on one, nomic on the
other), by a few questions. **Lesson**: the chunker matters as much as the embedder, and a ranking from
someone else's documents does not transfer to yours.

## 6. The bundled documents, with real models

ragcourt's own sample documents (13 pages about a made-up job queue), `gemma4` as writer and judge, 8
questions per kind. About 2 minutes. 36 questions kept; **no distractor questions survived**: the similar
passages in these small documents genuinely answer the same questions, and the judge rightly dropped them.

| Step | Result |
|---|---|
| embedders | `mxbai-embed-large` 0.87 = `embeddinggemma` 0.83; `nomic-embed-text` 0.73, clearly worse |
| chunkers | `markdown` 0.93 = `recursive` 256 0.90 = `sentence` 0.87; `fixed` 0.88 and `recursive` 512 0.83 worse |
| retrievers | `dense` 0.93 = `bm25` 0.90 = `hybrid` 0.87 |
| rerankers | `llm` 0.97 = none 0.93 |

Small, clean documents: almost everything works, and ragcourt says "no significant difference" instead
of inventing a winner. Two misses were left, both `ranking.not_rescued` (the answer at rank 6 and 8);
the `llm` reranker fixed one of them, so that blame was **confirmed**.

## 7. Kubernetes documentation, with real models

25 pages of the Kubernetes "workloads" docs (Pods, probes, sidecars, disruptions…), 12 questions per kind,
default settings otherwise. **8 minutes 13 seconds** in all.

**Questions**: 233 drafts, 67 kept. The hardest kind was distractor (7 kept of 72 drafts: most were
answered by the look-alike passage too, or their quote was not copied exactly). Numeric drafts often
failed the code rules (19 of 34 drafts). With only 5 held-out distractor questions,
distractor was **too few to rank** and left out of the overall score.

**Leaderboards** (`recall_at_budget`, held-out, `=` tied with the top):

```text
embedders    nomic-embed-text 0.43 [0.33, 0.53]  = embeddinggemma 0.43  = mxbai-embed-large 0.36      no winner
chunkers     markdown 0.62 [0.50, 0.78]  = recursive 256 0.55  = fixed 0.50  = sentence 0.50
             recursive 512 0.43 [0.31, 0.55]  (clearly worse)                                       no winner
retrievers   bm25 0.70 [0.60, 0.78]  = hybrid 0.65;  dense 0.55 (clearly worse)                       no winner
             On paraphrase, dense leads.
rerankers    llm 0.80 [0.70, 0.90];  none 0.70                                                      winner: llm
```

What it tells you:
- **The chunker mattered**: the default `recursive` at 512 tokens was clearly the worst. Cutting by
  heading (`markdown`, 0.62) or smaller (`recursive` at 256, 0.55) did better on these docs, whose sections
  are short.
- **Keyword search beat meaning search overall** (`bm25` 0.70 vs `dense` 0.55): these questions are full of
  exact terms (`restartPolicy`, `PodDisruptionBudget`). But on paraphrase questions dense was clearly
  better. That is why `hybrid` is a safe choice here.
- **The reranker was the one clear win**: +0.10.
- **The search's own choice differed from the held-out winner at the last step**: on the 22 dev questions,
  `llm` and none could not be told apart, so the cheaper (no reranker) was carried forward, while the
  held-out board named `llm` the winner. Choosing on dev keeps held-out numbers honest; the price is that a
  small dev set can miss a real difference. With a clear held-out winner, take it, or write more questions.

**Ceilings** of the chosen pipeline:

```text
group       questions  chunker  retrieval  hit@k
overall            45     1.00       0.96   0.82
paraphrase          8     1.00       0.75   0.13
```

The 256-token chunker kept every answer whole. Retrieval lost 4%, ranking 14%: so the fix is ranking (the
reranker). Paraphrase questions are the weak spot: a quarter are not retrieved at all, and only 1 in 8
reaches the top 5.

**Why questions were missed** (real examples):

```text
[paraphrase] What auxiliary containers operate alongside the principal software unit…
  cause: retriever.keyword_only, confirmed
  evidence: BM25 does not retrieve the chunk; dense search ranks it 1
  fix: dense or hybrid retrieval: retriever dense finds it (measured in this run)

[paraphrase] What happens to a running application when its health check repeatedly fails…
  cause: ranking.not_rescued, confirmed
  evidence: retrieved at rank 15, below k = 5; no reranker
  fix: a reranker that lifts it, or a larger k: reranker llm finds it (measured in this run)

[exact_term] What is described under the section titled 'other-pod-conditions'?
  cause: ranking.not_rescued, indicated
  evidence: retrieved at rank 12, below k = 5; no reranker
  fix: a reranker that lifts it, or a larger k; measured here and not finding it either: reranker
```

The first is a question that uses none of the passage's words ("auxiliary containers" for *sidecar
containers*): exactly what keyword search can't do. 38% of the causes were **confirmed** by a measured
alternative.

**The audit** of the chosen chunker: 344 chunks; 303 without their heading (`context.no_heading`), 26
splitting a code block, 7 splitting a table, none over the embedder's limit. The missing headings suggest
trying `markdown` at 256 tokens next:

```text
ragcourt rank k8s_docs/ --chunkers "markdown:size=256,overlap=32;recursive:size=256,overlap=32" --rerankers llm
```

## 8. What the real runs changed in ragcourt

Every problem below was found by these runs, then fixed and covered by a test:

- The judge wrongly rejected keyword searches as "not a question": its prompt now says they are valid.
- Distractor questions were almost never kept: the code check was too strict and the judge's prompt was a
  confusing double negative. Both rewritten.
- Numeric questions kept asking for the version number in a page's repeated header: repeated headers and
  footers are no longer shown to the writer.
- Ollama's silent truncation (section 4) and HTML menus (section 3).
- A second run made one needless call to measure the input limit: the limit is now remembered.
- An interrupted run and a resumed one now give exactly the same results (checked with real models).

## 9. Public datasets for testing RAG

If you want to test retrieval on data with known answers (not your own), these public sets have gold
answers as exact quotes in whole documents ([0005](../design/history/0005-rag-datasets.md)):

| Dataset | What | Why it is useful |
|---|---|---|
| [Chroma chunking evaluation](https://github.com/brandonstarxel/chunking_evaluation) (MIT) | 5 texts, 472 questions with character spans | the closest to ragcourt's format; easy questions |
| MultiHop-RAG (Hugging Face `yixuantt/MultiHopRAG`, ODC-BY) | 609 news articles, 2,556 questions | multi-document and unanswerable questions; evidence found verbatim |
| [LegalBench-RAG](https://github.com/ZeroEntropy-AI/legalbenchrag) (MIT) | contracts, character spans | long, repetitive text and look-alike clauses: hard for chunkers |
| [ConditionalQA](https://github.com/haitian-sun/ConditionalQA) | gov.uk pages | real HTML, conditions, questions with no answer |
| Qasper (Hugging Face `allenai/qasper`, CC BY 4.0) | NLP papers | long structured documents |

You can turn one into ragcourt questions with `--questions-file` (chapter 14): each gold excerpt becomes a
`quote`. A ready-made converter is planned.

Next: [troubleshooting](20-troubleshooting.md).
