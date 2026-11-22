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
  fix: dense or hybrid retrieval: with retriever dense it reaches the top k (measured in this run)

[paraphrase] What happens to a running application when its health check repeatedly fails…
  cause: ranking.not_rescued, confirmed
  evidence: retrieved at rank 15, below k = 5; no reranker
  fix: a reranker that lifts it, or a larger k: with reranker llm it reaches the top k (measured in this run)

[exact_term] What is described under the section titled 'other-pod-conditions'?
  cause: ranking.not_rescued, indicated
  evidence: retrieved at rank 12, below k = 5; no reranker
  fix: a reranker that lifts it, or a larger k; measured here, and it misses the top k there too: reranker
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

## 8. Chroma's benchmark, with its own gold questions

A test where ragcourt's question writer plays no part: Chroma's chunking benchmark (5 texts, 1.4 million
characters: a State of the Union speech, Wikipedia articles, chat logs, finance reports, PubMed papers)
comes with 472 questions whose answers are exact character spans. Converted to `--questions-file` (the
first gold span of each question as its quote) and run with `--questions 0`, so no question was written or
judged. 31 minutes in all, 400 MB of memory at most.

```text
embedders    embeddinggemma 0.56 [0.51, 0.62]  = mxbai-embed-large 0.55  = nomic-embed-text 0.53    no winner
chunkers     recursive 256 0.70 [0.64, 0.75]  = fixed 256 0.69  = sentence 256 0.68
             recursive 512 0.53, markdown 512 0.53 (clearly worse)                                 no winner
retrievers   hybrid 0.78 [0.73, 0.82]  = bm25 0.77;  dense 0.70 (clearly worse)                      no winner
rerankers    llm 0.81 [0.77, 0.86];  none 0.70                                                    winner: llm
```

What it showed:
- **Again, chunk size first**: 256-token chunks of any kind beat 512-token ones by 0.15 to 0.17. These
  texts have few headings, so `markdown` behaves like the 512-token `recursive`.
- **The embedders were within 0.03 of each other** on 270 held-out questions, and the intervals say so.
  Picking an embedder by leaderboard reputation would have been noise here.
- **A bug in ragcourt**: at the retriever step, `dense` was carried forward although `hybrid` and `bm25`
  were separably better on held-out questions. On dev all three were tied, and the tie-break put "fewer
  tokens per question" before the dev score. Fixed: among ties the higher dev score now comes first, and a
  choice that held-out questions show to be behind is pointed out (chapter 11).
- **The `llm` reranker helps overall and hurts sometimes**: it lifted the score by 0.11 but pushed 7
  answers out of the top 5 (`ranking.reranker_demoted`, confirmed: without the reranker they were found),
  several from rank 1 to below 15 on dense PubMed passages.
- **67 of the 472 questions were dropped as ambiguous**: their quote appears twice in the same file. User
  questions may now give `start`, the quote's character offset, so a dataset with gold spans converts
  whole (chapter 14).
- **The estimate was far off**: it said 2 minutes and took 31, because it did not count your own questions
  for reranking. Fixed.

## 9. FastAPI documentation, the full default run

The whole of FastAPI's English documentation: 159 Markdown pages, 1.5 MB of text (the 250 images,
stylesheets and scripts beside them were skipped). Half of the text is one 742 KB changelog. Everything at
its default: 90 questions per kind, three embedders, five chunkers, three retrievers, the `llm` reranker.

**Questions**: 1,985 drafts, 434 kept, 44 minutes. The changelog's bullet points (`* 📝 Update docs …
PR [#16032](https://…)`) were drafted again and again and rejected as "not a sentence" because of their
Markdown links: two fixes followed (links are prose now, and passages are taken one document at a time).
Distractors kept 2 of 164 drafts: these docs repeat themselves, so the look-alike passage usually answers
the question too. That kind now stops after 60 drafts when under 1 in 20 is kept, instead of asking for an
hour.

```text
embedders    embeddinggemma 0.37 [0.31, 0.42]  = mxbai-embed-large 0.33;  nomic-embed-text 0.32      no winner
chunkers     markdown 512 0.55 [0.50, 0.60];  sentence 0.46, recursive 256 0.45, fixed 0.45,
             recursive 512 0.33                                                           winner: markdown
retrievers   hybrid 0.63 [0.59, 0.68]  = bm25 0.63;  dense 0.55                                   no winner
rerankers    llm 0.66 [0.62, 0.71]  = none 0.63                                                    no winner
```

**What it showed:**
- **Structure wins on structured text.** Cutting at headings (`markdown`) beat every size-based chunker
  by 0.09 or more, and the default `recursive` at 512 tokens was worst again.
- **The overall score hid a failure.** `bm25` and `hybrid` tied overall, and the dev questions chose
  `bm25`. But on paraphrase questions `bm25` scored **0.02**, against `hybrid`'s 0.18: keyword search
  cannot match "What are some applications for sending data in segments?" to a page that says "use it to
  stream large binary files", which dense search ranks first. The ceilings said the same (paraphrase: 38%
  retrieved, 27% in the top 5), and 32 of the 66 misses were `retriever.keyword_only` on paraphrases. ragcourt now prints, under each board:

  ```text
  Note: on paraphrase questions this choice scores 0.02, separably below markdown:size=512,overlap=64 |
  mxbai-embed-large | dense | none (0.22). If those questions matter to you, prefer it.
  ```

  If your users ask in their own words, take `hybrid` here.
- **The reranker rescued some of it**: paraphrase went from 0.02 to 0.25 with `llm`, at about 2 seconds a
  question.
- **One refused call ended a 30-minute step.** Ollama answered `500: prediction aborted, token repeat limit
  reached` to one reranker call, three times, and the run stopped. Now that call is tried once more with
  sampling, and if it still fails, that question keeps its retrieval order and the failure is counted
  under the board.
- **The time estimate said 125 minutes; the run took about 70** (44 writing questions, 4 embedding, 20
  reranking). The estimate now uses these measurements. Running `rank` again, with the questions and
  embeddings reused, took 23 minutes, nearly all of it the reranker. Memory never passed 720 MB.

## 10. What the real runs changed in ragcourt

Every problem below was found by these runs, then fixed and covered by a test:

- The judge wrongly rejected keyword searches as "not a question": its prompt now says they are valid.
- Distractor questions were almost never kept: the code check was too strict and the judge's prompt was a
  confusing double negative. Both rewritten.
- Numeric questions kept asking for the version number in a page's repeated header: repeated headers and
  footers are no longer shown to the writer.
- Ollama's silent truncation (section 4) and HTML menus (section 3).
- A second run made one needless call to measure the input limit: the limit is now remembered.
- An interrupted run and a resumed one now give exactly the same results (checked with real models).
- Run on Chroma's benchmark and the FastAPI docs (sections 8 and 9): the tie-break among tied entries, the
  notes under each board, user questions with a `start` offset, questions spread over documents,
  Markdown links in quotes, the early stop for hopeless kinds, surviving a refused call, and measured time
  estimates.
- From a security review and a new user's test of the built package: a key never follows a redirect,
  links out of your documents folder are skipped, terminal control characters from documents or models
  are shown as escapes, no traceback for a wrong setting or a missing model, one ragcourt per working
  folder, and chunking in linear time (a 4 MB file: 80 seconds before, 9 now).

## 11. Public datasets for testing RAG

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
