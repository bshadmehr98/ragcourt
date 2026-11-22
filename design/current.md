# ragdoctor: the design (0.1)

This is the design as it stands, written from the owner's brief of 2026-11-22
([`history/0001-owner-brief.md`](history/0001-owner-brief.md)) and proposed with
[`changes/0001-initial-design.md`](changes/0001-initial-design.md). Its §16 lists the guarantees the tests
check; §17 says what is built and what is still planned. The smaller choices are in
[`decisions.md`](decisions.md). Section numbers are stable: code comments and the skills refer to them
("design §9.1").

**Status:** proposed; nothing is built.

## 1. What it does

ragdoctor is a command-line tool for people building retrieval-augmented generation. Given a folder of
their own documents, it **audits** how a chunker cuts them (no model needed), **ranks** chunkers,
embedding models, retrievers and rerankers by measuring them against questions whose gold answers are
exact quotes from the documents, **explains** each failed question by naming the one stage that lost it
and what would fix it, and lets a model act as a **doctor** that proposes, and may write, a chunker that
is then measured like any other. Code decides every number and every blame; a model only writes
questions and, in `doctor`, suggestions.

### Goals

- A first useful result in under a minute with no API key: `ragdoctor audit <folder>` (brief §1; D-006).
- Numbers measured on the user's documents, with their uncertainty, never general advice (brief §1, §5).
- Every failed question has one named cause and a suggested fix (brief §1, §4).
- A newcomer reads the whole codebase in an evening and adds a stage in one file (brief §1, §7, §9).

### Non-goals (0.1)

Answer generation and its evaluation; model judges of any kind; vector databases (indexes are in memory);
images, audio, video and scanned documents; a hosted service; telemetry; a web server; a full grid
search; fine-tuning anything (brief §11).

### Who it is for

A developer with a few dozen to a few thousand documents (up to roughly 50 MB of text) who must choose
a chunker, an embedding model, a retriever and a reranker, and wants evidence from their own corpus.

## 2. Concepts and words

| Word | Meaning |
|---|---|
| **document** | one source file loaded as text, with a stable id (its path relative to the corpus folder) |
| **span** | a `[start, end)` pair of character offsets into one document's text |
| **chunk** | a string a chunker returned, with the span the pipeline found for it (§4.2) |
| **stage** | one implementation of one of four **kinds**: chunker, embedder, retriever, reranker (§7) |
| **pipeline** | one chunker, one embedder (or none, for a lexical retriever), one retriever and one reranker (or none) |
| **question** | a question with its **gold quote**: a span of one document that answers it (§6) |
| **style** | how a question is phrased: `paraphrase`, `keyword` or `user` |
| **split** | `dev` (used to choose) or `held-out` (used to report) (§6.4) |
| **hit** | a chunk whose span contains the whole gold quote (§8.2) |
| **depth** | how many candidates the retriever returns: 50 (brief §4) |
| **k** | how many chunks the pipeline returns in the end: 5 by default |
| **miss** | a question with no hit in the top k |
| **blame** | the stage a miss is attributed to: `chunker`, `retrieval` or `ranking` (§9) |
| **ceiling** | the best Hit@k a pipeline could reach if every stage after a given one were perfect (§9.2) |
| **check** | one audit rule with a stable code, such as `cut.mid_sentence` (§5.1) |
| **measured / estimated** | a token count from the embedder's own tokenizer, or from the fallback estimate (§4.3) |
| **run** | one `rank` invocation: its plan, its estimate, its results file (§13.3) |

## 3. Architecture

One Python package, `ragdoctor`, standard library only in its core (D-003). No services, no framework.

### 3.1 Layers

```text
types, errors      layer 0  dataclasses and protocols, no logic
stages             layer 1  the registry and one file per stage
core   |   io      layer 2  core: pure functions; io: files, the model client, the cache, reports
commands           layer 3  audit, rank, explain, doctor: one file each
cli                layer 4  argument parsing and printing
```

A module imports only from layers below its own. `core` and `io` never import each other: a command
reads with `io`, computes with `core`, and writes with `io`. Within `stages`, an implementation imports
only the registry (`ragdoctor.stages`), never another implementation; only the pipeline (`core`) joins
stages. A command never imports another command. Nothing imports `cli` or `testing`. The package root
(the public API) may import from every layer except `commands` and `cli`. `scripts/check_layers.py`
enforces all of this and runs in `scripts/check.sh`.

`core` is pure in this sense: its functions take values and callables and return values; they never open
files, read the clock or the environment, or touch the network. The callables they receive (an embedder's
`embed`, the cached wrapper around it) may do I/O; `core` does not know.

Stages that need a model (an endpoint embedder, an endpoint reranker) receive a client through the
`ModelClient` protocol declared in `types` (§11.1), so they never import `io`.

### 3.2 Modules

| Module | Holds | Design |
|---|---|---|
| `types.py` | `Document`, `Chunk`, `Question`, `Pipeline`, `Ranked`, `MetricRow`, `Blame`, `Finding`, `Estimate`, the four stage signatures, `ModelClient` | §2 |
| `errors.py` | `RagDoctorError` and its subclasses | §14 |
| `stages/__init__.py` | the four decorators, the registry, loading the user's folder | §7.2 |
| `stages/chunkers/*.py` … `stages/rerankers/*.py` | one stage per file | §7.3, §7.4 |
| `core/offsets.py` | finding chunk spans in the source | §4.2 |
| `core/audit.py` | the audit checks | §5 |
| `core/pipeline.py` | running one pipeline over questions | §8.1 |
| `core/metrics.py` | every metric | §8.3 |
| `core/stats.py` | bootstrap intervals and ties | §8.4 |
| `core/blame.py` | blame, ceilings, fixes | §9 |
| `core/search.py` | the greedy plan and its estimate | §10 |
| `io/loaders.py` | reading documents | §4.1 |
| `io/config.py` | `ragdoctor.toml` | §3.3 |
| `io/client.py` | the one model client | §11 |
| `io/cache.py` | the embedding cache | §10.2 |
| `io/questions.py` | generating, validating and storing questions | §6 |
| `io/report.py` | the results file, terminal tables, the HTML report | §13 |
| `commands/audit.py`, `rank.py`, `explain.py`, `doctor.py` | one command each | §5, §8–§10, §9, §12 |
| `cli.py` | `ragdoctor …` | §13.1 |
| `testing/` | `FakeEmbedder`, `ScriptedModel`, the bundled corpus | §15.2 |

### 3.3 Files

Everything ragdoctor writes goes in `.ragdoctor/` beside the corpus (or `--workdir`): `cache.sqlite`
(embeddings, §10.2), `questions.jsonl` (§6.5), `runs/<run-id>/results.json` and `report.html` (§13),
`doctor/` (§12). The optional `ragdoctor.toml` in the project names endpoints, models, prices, stages to
consider, `k` and the budget; keys are named by environment variable (`api_key_env = "OPENAI_API_KEY"`),
never written in the file (D-016).

## 4. Documents and chunks

### 4.1 Loading documents

`.md`, `.markdown`, `.txt`, `.rst` and `.html`/`.htm` (text extracted with the standard library's
`html.parser`, keeping headings as Markdown-style `#` lines so heading checks work the same). Files are
read as UTF-8 (a file that fails is reported and skipped, never guessed). Line endings are normalised to
`\n`; nothing else in the text is changed, so offsets are offsets into what the user wrote. Hidden
folders and `.ragdoctor/` are skipped. PDF is not in 0.1 (D-022).

### 4.2 Offsets: from strings to spans

A chunker returns strings; the pipeline finds where each one is (brief §7):

1. Search for the chunk's text in the document starting at the previous chunk's start + 1 (so overlapping
   chunks are found, and repeated text is matched in reading order).
2. If not found exactly, search again with runs of whitespace treated as equal (a chunker that strips or
   joins lines still maps back); the span covers the original characters.
3. If still not found, the chunker is invalid for this document: `ChunkNotInSource` names the chunker,
   the document, the chunk's index and its first 80 characters. A chunker that changes words, adds text
   (a heading prefix, a summary) or reorders text cannot be evaluated in 0.1 (§18; D-010).

Empty and whitespace-only strings are dropped and counted. Chunks are kept in the order returned.

### 4.3 Token counts

Chunk sizes are counted in the **embedder's own tokens** (brief §5). An embedder states its tokenizer:
`tiktoken:<encoding>` or `hf:<tokenizer id>` (both through the optional `tokens` extra, loaded from a
local file or a one-time download the user starts), or a function of its own. When the tokenizer cannot be
loaded, sizes use the fallback estimate (characters / 4) and every size and every "over the limit" flag
from it is labelled **estimated** in every output; a measured count is labelled **measured** (D-008).

Token-level metrics against the gold quote (§8.3) use a separate, fixed **reference tokenization** (words
and punctuation by a regular expression, on the source text), so they are comparable across embedders
(D-009).

## 5. Audit

`ragdoctor audit <folder> [--chunker NAME[:k=v,…]]… [--embedder NAME] [--show DOC]`. No model, no
network, no key. With no `--chunker`, every built-in native chunker is audited with its defaults; the
input limit and tokenizer come from `--embedder` (a name in the built-in table of known models, or the
configured one), or the check `size.over_limit` is skipped and the output says so.

### 5.1 Checks

Each check is a function in a table in `core/audit.py`, with a stable code (brief §2; D-024 for the
thresholds, all overridable in `ragdoctor.toml`):

| Code | Flags a chunk that… |
|---|---|
| `cut.mid_sentence` | ends where the source continues the same sentence: the last non-space character is not sentence-ending punctuation, a closing bracket or quote, or the end of a block (a blank line, a heading, the end of the document) |
| `context.no_heading` | lies under a heading (Markdown `#`, setext, or HTML `h1`–`h6`) that appears neither in the chunk nor, for the chunk's first section, at its start |
| `split.table` | contains part, but not all, of a Markdown or HTML table's rows |
| `split.code` | contains part, but not all, of a fenced or indented code block |
| `boilerplate.repeated` | consists mostly (≥ 50% of its lines) of lines that repeat across ≥ 30% of the documents (headers, footers, navigation) |
| `duplicate.near` | has word-5-gram Jaccard similarity ≥ 0.9 with an earlier chunk (MinHash-free exact shingles below 20k chunks, a fixed-seed MinHash above) |
| `size.tiny` | has fewer than 20 tokens |
| `size.over_limit` | has more tokens than the embedder accepts, so the end would be silently truncated (measured or estimated, §4.3) |

### 5.2 Output

A summary table per chunker: chunks, size in tokens (median, p95, max, labelled measured or estimated),
and the count and share of chunks per check. Then the worst examples per check (document, offsets, the
first and last 60 characters). `--show DOC` prints the document with chunk boundaries marked inline
(`⟦12⟧` at each start, `⟧` at each end, flagged chunks named), so the user sees the cuts on their own
text. `--json` writes the same as data. The exit code is 0, or 3 with `--fail-on CODE…` when one of those
checks fires (for CI).

## 6. Questions and gold answers

### 6.1 Generation

`ragdoctor rank` (or `ragdoctor questions` alone) asks the configured chat model to write questions.
Passages are sampled from the documents (not from any chunker's output: brief §3), with a fixed seed,
proportional to document length: windows of about 2,000 characters cut at paragraph boundaries. For
each window the model returns JSON: a list of `{question, quote, style}` with `style` in `paraphrase`
(different words from the source) or `keyword` (the terms a user would type into a search box). The
prompt asks for a quote of one to three sentences that answers the question on its own. The target is
100 questions by default (`--questions N`).

### 6.2 Validation and filters

Applied in order, each drop counted by reason and reported:

1. **Not verbatim:** the quote is searched in the window's document, first exactly, then with
   whitespace runs treated as equal (D-010). Not found: dropped (brief §3). Found: the gold is the span.
2. **Too short or too long:** quotes under 5 or over 120 reference tokens.
3. **Duplicate:** a question whose quote overlaps an earlier question's quote by more than half, or whose
   text is a near-duplicate of an earlier question.
4. **Answerable without the documents:** the model is asked the question with no documents; if its answer
   contains at least half of the quote's content words (reference tokens minus a fixed stop-word list),
   the question is dropped. Computed by code, not judged by a model (D-012).

The question set never refers to chunks; it depends only on the documents' text. If a document changes,
its questions are revalidated against the new text and dropped when the quote is gone.

### 6.3 The user's own questions

`--questions-file my.jsonl`: one JSON object per line with `question` and `quote`, and optionally
`document` (otherwise every document is searched; a quote found in more than one place is rejected as
ambiguous unless `document` is given). They are validated by rule 1 only and tagged `style: user`; user
questions are never dropped for being answerable without the documents. A question without a quote
cannot be scored and is rejected with that reason (D-025).

### 6.4 Splits

Each question gets a split from a hash of its id and the run's seed: half `dev`, half `held-out`
(`--holdout 0.5`), stratified by document so both splits cover the corpus. The search (§10) reads only
dev results; every number in a leaderboard, every interval and every blame in `explain` is from held-out
questions. With fewer than 30 held-out questions the output warns that intervals will be wide (D-011).

### 6.5 The question file

`.ragdoctor/questions.jsonl`, first line a header `{"format_version": "1", "corpus_hash": …, "model": …,
"seed": …, "dropped": {reason: count}}`, then one question per line: `id`, `question`, `style`,
`document`, `start`, `end`, `quote`, `split`. Reused by later runs while the corpus hash matches; a newer
`format_version` is refused with a message.

## 7. Stages

### 7.1 The four kinds

| Kind | Signature (in `types`) | Notes |
|---|---|---|
| chunker | `(text: str) -> list[str]` | the pipeline finds offsets (§4.2) |
| embedder | an `Embedder`: `model`, `max_tokens`, `tokenizer`, `embed(texts: list[str]) -> list[list[float]]` | called in batches; never caches (the cache wraps it, §10.2) |
| retriever | `(chunks: list[str], vectors: list[list[float]] \| None, embed_query) -> search(query, depth) -> list[(index, score)]` | builds its index once per chunk set |
| reranker | `(query: str, candidates: list[str]) -> list[float]` | scores; the pipeline sorts |

Each takes its parameters as keyword arguments with defaults (`recursive:size=512,overlap=64`). Ties in
scores are broken by chunk index, so results are deterministic.

### 7.2 Registration and the user's folder

```python
from ragdoctor.stages import chunker

@chunker("by_paragraph")
def by_paragraph(text: str, min_chars: int = 200) -> list[str]:
    ...
```

`@chunker`, `@embedder`, `@retriever` and `@reranker` register a function (or, for an embedder, a factory
returning an `Embedder`) under a name; registering a name twice is an error that names both files. The
built-ins are imported from `stages/<kind>/`; the user's own are loaded from `ragdoctor_stages/` in the
project (or `--stages DIR`), every `.py` file in it imported in sorted order. These are the user's own
code and run in-process like any Python they write (D-018); code written by a model is different (§12).

### 7.3 Built-in stages

| Kind | Name | Needs |
|---|---|---|
| chunker | `fixed` (tokens, with overlap) | — (uses the embedder's tokenizer, or the estimate) |
| chunker | `recursive` (paragraphs, lines, sentences, words, down to a size) | — |
| chunker | `sentence` (whole sentences packed to a size) | — |
| chunker | `markdown` (sections by heading, heading kept, then `recursive` inside) | — |
| embedder | `endpoint` (any OpenAI-compatible `/embeddings`) | an endpoint |
| retriever | `dense` (cosine, exact, in memory) | an embedder |
| retriever | `bm25` (pure Python) | — |
| retriever | `hybrid` (reciprocal-rank fusion of `dense` and `bm25`) | an embedder |
| reranker | `none` | — |
| reranker | `endpoint` (a `/rerank` endpoint in the Jina/Cohere format: vLLM, llama.cpp, TEI, Jina, Cohere) | an endpoint (D-015) |

### 7.4 Adapters and extras

Thin adapters, each one file, each behind an optional extra imported only inside the function:

| Extra | Brings | Stages |
|---|---|---|
| `tokens` | `tiktoken`, `tokenizers` | exact token counts (§4.3) |
| `local` | `sentence-transformers` | embedder `st` and reranker `cross-encoder`, in-process (D-007) |
| `chonkie` | `chonkie` | chunkers `chonkie.token`, `chonkie.sentence`, `chonkie.recursive`, `chonkie.semantic` |
| `langchain` | `langchain-text-splitters` | chunkers `langchain.recursive`, `langchain.markdown` |

A missing extra gives `ExtraMissing` naming `pip install 'ragdoctor[<extra>]'`.

## 8. The pipeline and metrics

### 8.1 Running one pipeline

For a pipeline and a question set: chunk every document and find spans (§4.2); embed every chunk
through the cache (§10.2); build the retriever; for each question, retrieve `depth` = 50 candidates,
rerank them if a reranker is set, and keep the order. The pipeline returns, per question, the ranked
chunk spans with their scores, the retrieval rank and the final rank of the first hit, and timing.
Everything after the embedding calls is in `core` and deterministic.

### 8.2 Relevance

A chunk is a **hit** for a question when its span (in the quote's document) contains the whole quote.
For graded and token measures, a chunk's relevance is the fraction of the quote's reference tokens inside
its span (D-013).

### 8.3 Metrics

Per question, then averaged over held-out questions:

| Metric | Definition |
|---|---|
| `hit_at_k` | 1 if a hit is in the top k |
| `mrr` | 1 / rank of the first hit in the top `depth`, else 0 |
| `ndcg_at_k` | nDCG over the top k with graded relevance (§8.2); ideal = the best k chunks of this chunking |
| `recall_at_k` | share of the quote's reference tokens covered by the union of the top-k spans |
| `token_precision_at_k` | quote tokens in the top-k spans / all tokens in the top-k spans (overlaps counted once) |
| `token_iou_at_k` | quote tokens covered / (quote tokens ∪ tokens of the top-k spans) |
| `recall_at_budget` | `recall_at_k` with chunks taken in rank order until a fixed budget of reference tokens (default 400; the last chunk is cut at the budget), so large chunks cannot win by size (brief §5) |

And per pipeline: `vectors` (chunks embedded), `chunk_tokens` (median and p95, measured or estimated),
`tokens_per_query` (tokens in the top k), `latency_ms` (p50 and p95 per query, excluding cached
embedding), `index_ms`, and `cost` (from the user's prices per million tokens; `unknown` when a price is
not given, never 0; D-020).

### 8.4 Uncertainty and ties

Every averaged metric is reported with a 95% interval from a bootstrap over held-out questions (2,000
resamples, fixed seed). The leaderboard is sorted by the chosen metric (`recall_at_budget` by default;
`--metric`). The top two are compared with a **paired** bootstrap of the per-question difference: if its
95% interval contains 0, the output says "no significant difference" between them, lists every entry
not separable from the top the same way, and calls none of them the winner. A smaller or cheaper entry
among the tied is pointed out as such (D-011).

## 9. Blame and explain

### 9.1 Blame rules

For each held-out miss of the chosen pipeline, computed by code from spans and ranks (brief §4):

1. **`chunker`**: the quote is intact in no chunk (no chunk's span contains it). Evidence: the chunks
   that hold parts of it, with the cut positions.
2. **`retrieval`** (the embedder or the retriever): a hit exists but is not in the retriever's top 50.
   Evidence: the hit's retrieval rank (computed over all chunks) and the score gap to the 50th.
3. **`ranking`**: a hit is in the top 50 but below k after reranking (or after retrieval when there is no
   reranker). Evidence: its rank before and after the reranker.

Exactly one applies to each miss. `retrieval` is one stage for the embedder and the retriever together;
§9.3 separates them when the measurements can (D-014).

### 9.2 Ceilings

For the chosen pipeline, on held-out questions: the **chunker ceiling** (share with an intact quote in
some chunk), the **retrieval ceiling** (share with a hit in the top 50) and **Hit@k**. They are
non-increasing by construction, and the gaps between them are the share of questions each stage lost.
Each has its interval.

### 9.3 Fixes

A fix is suggested from measurements already made in the run, never from a model:

- For each miss, the configurations from the search (§10) that hit this question, preferring the one that
  changes only the blamed stage, then the cheapest. "Chunker `sentence:size=384` keeps this quote whole
  (measured on this question)". For `retrieval`, a measured embedder that ranks the hit in the top 50
  names the embedder; a measured retriever (`bm25`, `hybrid`) that does names the retriever.
- When no measured configuration hits it, the stage's general fix is given and labelled "not measured":
  a chunker that respects sentences or headings, a larger depth, a reranker. `explain` always names one
  cause and one fix (brief §1).

`ragdoctor explain [RUN]` prints, per miss: the question, the quote and its place, the cause with its
evidence, the fix; then the counts per cause. `--show ID` prints the quote's surroundings with the chunk
boundaries marked (§5.2).

## 10. Search, cache, estimate and budget

### 10.1 Greedy search

Greedy by stage, embedders first (brief §6), on dev questions, by the chosen metric:

1. **Embedders:** each candidate embedder with the default chunker (`recursive:size=512,overlap=64`), the
   `dense` retriever and no reranker.
2. **Chunkers:** each candidate chunker (and its listed parameter values) with the best embedder.
3. **Retrievers:** `dense`, `bm25`, `hybrid` with the best chunker and embedder.
4. **Rerankers:** `none` and each candidate reranker on the best so far.

A stage's best is the top entry on dev; when entries are tied (§8.4), the cheaper, then the smaller, then
the first listed is kept and the tie is reported. Candidates come from `ragdoctor.toml` or flags; by
default every available built-in. Every evaluated configuration's held-out numbers appear in that stage's
leaderboard; the "best overall pipeline" is the last step's choice, reported on held-out questions.

### 10.2 The cache

Embeddings are cached in `.ragdoctor/cache.sqlite` by `sha256(model identity + "\0" + text)`, where the
model identity is the endpoint's base URL and model name (or the local model's name and revision), and
the vector is stored as packed float32 with its dimension. A cached embedding is never sent again; a
second identical run makes no embedding calls. The cache has its own version; a layout change starts a
new file. `--no-cache` and `ragdoctor cache clear` exist (D-016).

### 10.3 Estimate and budget

Before any model call, `rank` prints the plan (stages and candidates per step), the number of chunks and
tokens to embed after the cache, the number of chat calls for questions, and an estimate of time and cost:
time from a calibration call (one small batch per endpoint, timed) or from the last run's timing; cost from
the configured prices, or `unknown`. `--budget-usd` and `--budget-minutes` stop the run before a step
that would exceed them: the steps done are reported, the step not run is named, and nothing is presented
as complete. Without `--yes`, a run estimated over one minute or over $0 asks before starting.

## 11. Models

### 11.1 The one client

`io/client.py` speaks the OpenAI-compatible HTTP API with the standard library (`urllib`): chat
completions (with JSON output where the server supports it, validated either way), embeddings, and the
`/rerank` route of §7.3. "Local models" means a local server speaking this API (Ollama, llama.cpp, vLLM,
LM Studio) or the in-process models of the `local` extra; both go through the same `ModelClient`
protocol in `types` (D-007). Retries: timeouts, 429 and 5xx only, three times with backoff; other
failures stop with `EndpointError` naming the endpoint, the status and what to check. Batches are sized
to the endpoint's limits and the model's input limit.

### 11.2 Privacy

Nothing leaves the machine unless the user configured an endpoint, and then only to that endpoint: the
document windows for question generation and for `doctor`, the questions (alone, for the
answerable-without-documents check), chunk texts for embedding and reranking. `audit` never opens a
network connection. Keys are read from the environment variable the configuration names. No telemetry,
no update check. Logs never contain document text or keys. `docs/privacy.md` lists every call.

## 12. Doctor

`ragdoctor doctor <folder>`:

1. **Sample:** up to 8 documents (fixed seed, by size and type), each cut to about 4,000 characters.
2. **Describe:** the chat model returns JSON: the structure it sees (headings, tables, code, lists,
   boilerplate, average paragraph length) and up to three recommended built-in chunkers with parameters.
   Recommendations naming unknown stages or parameters are dropped and reported.
3. **Write (optional):** the model may return one chunker file, `def chunk(text: str) -> list[str]`,
   standard library only. It is saved to `.ragdoctor/doctor/<sha256-prefix>.py`.
4. **Ask:** the code is printed in full with its SHA-256, and the user is asked to run it (`y/N`). It
   never runs without that answer, or `--approve <sha256>` matching exactly this file (D-017).
5. **Run isolated:** in a subprocess (`python -I`, a temporary working folder, an environment without
   keys or proxies), one document at a time on stdin, JSON out, with a timeout (10 s per document by
   default) and an output size limit. This is isolation from hangs and crashes, not a security sandbox:
   approval is the safety step, and the output says so.
6. **Validate:** a list of non-empty strings, each found in the source (§4.2); otherwise the chunker is
   rejected with the first failure shown.
7. **Measure:** the generated chunker and the recommendations join the chunker step of §10.1 with the
   baselines (the built-ins) on the same questions. It is reported better only when the paired interval
   says so on held-out questions; otherwise "no significant difference" or "worse" is printed with the
   numbers (brief §2).

## 13. Output and the command line

### 13.1 Commands

```text
ragdoctor audit <folder> [--chunker SPEC]… [--embedder NAME] [--show DOC] [--json] [--fail-on CODE…]
ragdoctor questions <folder> [--questions N] [--questions-file FILE]
ragdoctor rank <folder> [--questions-file FILE] [--metric NAME] [--k N] [--budget-usd X] [--budget-minutes M] [--yes] [--html]
ragdoctor explain [RUN] [--show QUESTION-ID]
ragdoctor doctor <folder> [--approve SHA256]
ragdoctor cache clear
```

Common: `--workdir`, `--config`, `--stages DIR`, `--seed`, `--json`, `-q`. Exit codes: 0 done, 1 error, 2
usage, 3 a `--fail-on` check fired, 4 stopped by the budget.

### 13.2 Terminal output

Plain text tables, no colour when not a terminal, every number with its interval and its label
(measured, estimated, unknown).

### 13.3 The results file

`.ragdoctor/runs/<run-id>/results.json`, `format_version "1"`: the run's settings and seed, the
corpus and question-set hashes, the plan and the estimate, every evaluated configuration with its
metrics (mean and interval, dev and held-out), per-question ranks for held-out questions, the ties, the
chosen pipeline, ceilings, blame per miss with its evidence and fix, the actual time and cost. `explain`
and the HTML report read only this file.

### 13.4 The HTML report

`rank --html` (and `ragdoctor report [RUN]`) writes one self-contained `report.html` from the results file:
the leaderboard per stage with interval bars and ties marked, the chosen pipeline and its ceilings, the
misses grouped by cause, each opening to the quote shown on its source text with the chunk boundaries,
and the audit summary of the chosen chunker. Standard library templating, inline CSS, a few lines of
inline JavaScript for filtering, no network requests when opened (D-019).

## 14. Errors and determinism

Errors are `RagDoctorError` subclasses: `ConfigError`, `ExtraMissing`, `ChunkNotInSource`,
`EndpointError` (retryable or not), `BudgetExceeded`, `FormatVersionError`, `GeneratedCodeRejected`.
Every message says what happened and what to do. With the same documents, questions, seed and stages, a
run gives the same results file except for timings and its run id.

## 15. Testing, docs and examples

### 15.1 Suites

The suites of CONTRIBUTING.md: unit, contract, integration and acceptance by default (offline,
deterministic), real models by hand (`real_model`).

### 15.2 The bundled corpus and the fakes

`tests/fixtures/corpus/` (also shipped as `ragdoctor.testing.corpus`): a dozen short documents written for
the tests, each with cases on purpose (a table, a code block, a running header, a near-duplicate, a long
section, plain prose), and a hand-checked `questions.jsonl`. `FakeEmbedder`: deterministic vectors from
hashed word n-grams with a tokenizer and a limit, so similar texts are close and results are stable.
`ScriptedModel`: returns scripted replies per request in order and records what it was sent, for
question generation, the closed-book check and doctor.

### 15.3 Examples

One file per concept, in reading order, run by `tests/e2e/`: `quickstart.py` (audit a folder),
`boundaries.py` (see the cuts), `own_chunker.py` (a stage in one file), `questions.py` (gold quotes,
drops, splits), `rank.py` (a leaderboard with intervals and ties), `budget_recall.py` (why size cannot
win), `blame.py` (one miss per cause), `cache_and_budget.py`, `report.py` (M3), `doctor.py` (M4).

### 15.4 Docs

The pages of [`docs/README.md`](../docs/README.md), with every Python block run by the tests. `docs/one-question.md`
follows one question from its document through generation, validation, the split, chunking, retrieval
and reranking to its blame and fix, with real output from the bundled corpus.

## 16. Guarantees (acceptance cases)

Each is a test `tests/e2e/test_ac<N>_<slug>.py` through the public API or CLI that fails if the feature
is removed.

1. **Audit needs nothing.** `ragdoctor audit` on the bundled corpus finishes with no network (sockets
   blocked), no key and no model, and reports every check of §5.1 on the document planted for it.
2. **Checks are precise.** Each check fires on its planted case and not on its planted near miss (a
   sentence ending in an abbreviation, a heading repeated in the chunk, a table kept whole).
3. **Offsets are found by code.** Overlapping chunks, repeated text and whitespace-changed chunks map to
   the right spans; a chunk not in the source fails with `ChunkNotInSource` naming the chunk.
4. **Sizes are labelled.** Sizes and `size.over_limit` from the embedder's tokenizer say `measured`; with
   the tokenizer unavailable they say `estimated`, everywhere they appear.
5. **Gold is verbatim.** A generated quote not found in its document drops the question, and the drop is
   counted by reason in the question file and the output.
6. **Gold is independent of chunking.** The same question file scores every pipeline; changing the
   chunker changes no question, quote or split.
7. **Closed-book questions are dropped.** A question the scripted model answers without the documents is
   dropped by the code rule of §6.2; a user's question never is.
8. **User questions are accepted** with quote validation; an ambiguous or missing quote is rejected with
   its reason.
9. **Search on dev, report on held-out.** Changing only held-out results never changes the chosen
   pipeline; every leaderboard number is from held-out questions.
10. **Metrics are right.** Every metric of §8.3 equals its hand-worked value on a fixture.
11. **Size cannot win.** A chunker that returns each document whole has `recall_at_k` of 1 where its
    chunks fit, and does not lead on `recall_at_budget`.
12. **Ties are said.** When the paired interval of the top two contains 0, the output says "no significant
    difference" and names no winner; when it does not, it names the winner.
13. **Blame is code and complete.** Every held-out miss has exactly one cause by the rules of §9.1; the
    planted cases give `chunker`, `retrieval` and `ranking` each; ceilings are non-increasing and their
    gaps equal the counts per cause.
14. **Every miss has a fix**, and a fix that names a configuration cites its measured result on that
    question; one that does not is labelled "not measured".
15. **The cache works.** A second identical run makes zero embedding calls; changing one document embeds
    only its chunks.
16. **The estimate comes first and the budget holds.** The estimate is printed before the first model
    call; a budget below the estimate stops before the step that would exceed it, exit code 4, with the
    finished steps reported and nothing called complete.
17. **Greedy, embedders first.** The plan and the results show the four steps of §10.1 in order, and
    only the configurations they list are evaluated.
18. **A stage is one file.** A chunker in the user's `ragdoctor_stages/` appears in `audit` and `rank`
    with no other change; a duplicate name fails naming both files.
19. **Nothing leaves without an endpoint.** With no endpoint configured no socket is opened in any
    command; with one, only its host is contacted; no key appears in any file ragdoctor writes or logs.
20. **Generated code is asked, isolated, validated and measured.** Doctor's chunker does not run when the
    answer is no or the hash differs; a hanging chunker is stopped by the timeout; an invalid output is
    rejected; a valid one is ranked with the baselines and called better only with a significant
    held-out difference.
21. **The default suite is deterministic.** Two runs on the bundled corpus give the same results file
    except for timings and the run id.
22. **The layers hold.** `scripts/check_layers.py` passes on the package and fails on each kind of
    forbidden import.
23. **The report is self-contained.** `report.html` opens with no network request and shows every
    leaderboard, interval, tie and miss of the results file.
24. **Examples and docs run.** Every example and every Python block in the docs runs; the walk-through of
    `docs/one-question.md` matches the bundled corpus's real output.

## 17. Implemented and planned

Updated as milestones land.

**Implemented:** nothing of the product yet. The repository, its gate (with the import-layer check of
§3.1) and its workflow exist.

**Planned** (the milestones of [`changes/0001-initial-design.md`](changes/0001-initial-design.md)):
M1 audit; M2 rank and explain; M3 the HTML report; M4 doctor.

## 18. Known limits (0.1)

Chunkers must return text found in the source (no added context or rewriting); text formats only (no
PDF, no images); one language's stop words and sentence rules (English) for the closed-book check and
`cut.mid_sentence`; exact in-memory search (fine to about 200k chunks); intervals are wide with few
held-out questions; the greedy search can miss a combination that only wins jointly; `retrieval` blame
does not separate the embedder from the retriever unless the search measured an alternative.
