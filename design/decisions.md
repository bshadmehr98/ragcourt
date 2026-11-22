# Decisions

Smaller choices and the owner's answers. "Owner" entries are the owner's words or choices; the others are
the designer's, open to the owner's review. Code comments refer to entries by number.

## Awaiting owner review

Design 0001 is proposed. These are the choices the owner should look at first; every other entry below is
open to review too.

| Id | The question | Status |
|---|---|---|
| [D-001](#d-001-the-name-ragdoctor) | Keep the working name `ragdoctor`, crowded by three RAG-diagnosis projects? | awaiting owner |
| [D-006](#d-006-the-first-minute-is-audit) | Is `audit` the "first useful result in under a minute with no API key"? | awaiting owner |
| [D-007](#d-007-one-client-local-means-a-local-server-or-the-local-extra) | "Local models" as local OpenAI-compatible servers, plus an optional in-process extra? | awaiting owner |
| [D-011](#d-011-the-split-and-the-intervals) | A 50/50 split by question and a paired bootstrap for ties? | awaiting owner |
| [D-012](#d-012-the-closed-book-check-by-code) | Deciding "answerable without the documents" by word overlap, not by a judge? | awaiting owner |
| [D-014](#d-014-retrieval-blame-is-one-stage) | Blame `retrieval` as one stage (embedder or retriever)? | awaiting owner |
| [D-017](#d-017-approving-generated-code) | Approval by `y/N` or by the code's hash; the subprocess is not a sandbox? | awaiting owner |
| [D-025](#d-025-user-questions-need-a-quote) | User questions must carry a quote and are never dropped as closed-book? | awaiting owner |
| [D-004](#d-004-repository-url) | The repository URL in `pyproject.toml`? | awaiting owner |

## The owner's answers (2026-11-22)

| Id | Decision | Who |
|---|---|---|
| D-002 | Python; the owner's toolchain (uv, hatchling, ruff with line length 110 and complexity 10, pyright strict for `src/`, pytest with 90% branch coverage, `scripts/check.sh` as the one gate) and the k8s-holmes workflow adapted (add-stage, real-model-tests, `RAGDOCTOR_ALLOW_MAIN`). | owner (the brief) |

## D-001: The name `ragdoctor`  (2026-11-22)

- **Question:** the brief calls `ragdoctor` a working name and asks for a clash check
  ([history/0000-research.md](history/0000-research.md) §3). PyPI `ragdoctor` is free, but `rag-doctor`
  is a published RAG failure-diagnosis tool (1.0.0, March 2026), and GitHub has
  thehalleyyoung/ragdoctor (RAG diagnostics with intervals and "prescriptions"), hanhanwu/RagDoctor
  (archived, root-cause tracing) and an npm `rag-doctor`. Users searching for one will find the others.
- **Choice:** keep `ragdoctor` as the package, import and command while the design is reviewed; every
  file uses it consistently so a rename is one search-and-replace before publishing. If the owner wants a
  clear name, candidates free on PyPI: `retrievalscope` (no GitHub repositories either), `chunkdoctor`
  (an unrelated Minecraft tool on GitHub). `ragblame` is free on PyPI but clashes in concept with
  pulkitnagpal/ragblame.
- **Status:** awaiting owner review; must be settled before the first publish.

## D-003: The core is the standard library alone  (2026-11-22)

- **Question:** k8s-holmes allows pydantic in the core. The brief asks for "types (dataclasses, no
  logic)", a first result in under a minute and a codebase read in an evening.
- **Choice:** no core dependencies. Dataclasses for types; `json`, `sqlite3`, `urllib`, `argparse`,
  `tomllib`, `html.parser`, `hashlib`, `random` for the rest. Vectors are lists of floats and cosine is
  plain Python (fast enough to about 200k chunks with a few hundred questions; §18). Every library is an
  extra (design §7.4). `numpy` would speed scoring and may become an optional accelerator later.
- **Status:** designer's choice.

## D-004: Repository URL  (2026-11-22)

- **Choice:** `https://github.com/bshadmehr98/ragdoctor` in `pyproject.toml` and `@bshadmehr98` in
  `CODEOWNERS`, as for k8s-holmes, until the owner says where the project lives.
- **Status:** awaiting owner review.

## D-005: No GPU lock script  (2026-11-22)

- **Choice:** the owner's GPU lock script is not copied (k8s-holmes did not have it either). In-process
  local models in the real-model tests may use a GPU; if they share a machine with the owner's other GPU
  work, the test can take the family's lock itself later.
- **Status:** designer's choice.

## D-006: The first minute is `audit`  (2026-11-22)

- **Question:** "a first useful result in under a minute, with no API key" (brief §1). `rank` needs
  questions, and generated questions need a chat model; without a key that means a local model server,
  which a newcomer may not have, and a model download takes longer than a minute.
- **Choice:** `ragdoctor audit <folder>` is the first useful result: no model, no network, seconds on
  thousands of documents. `rank` with no key works with a local server (Ollama and the like), or with
  the user's own questions, `bm25` and the `local` extra. The README quickstart is `audit`.
- **Status:** awaiting owner review.

## D-007: One client; "local" means a local server or the `local` extra  (2026-11-22)

- **Question:** "local models and any OpenAI-compatible endpoint … through one client" (brief §8).
- **Choice:** one `ModelClient` protocol (in `types`) with one HTTP implementation over `urllib` for the
  OpenAI-compatible API. Local servers (Ollama, llama.cpp, vLLM, LM Studio) speak that API, so they need
  nothing else. For people without a server, the `local` extra adds in-process `sentence-transformers`
  embedders and cross-encoder rerankers behind the same protocol. There is no in-process chat model in
  0.1: question generation and doctor need a server or an endpoint.
- **Status:** awaiting owner review.

## D-008: Token counts: the embedder's tokenizer, or labelled estimates  (2026-11-22)

- **Choice:** an embedder names its tokenizer (`tiktoken:<encoding>` or `hf:<id>`, through the `tokens`
  extra). A small built-in table maps well-known embedding models to their tokenizer and input limit, so
  `audit --embedder <name>` works without configuration. When the tokenizer cannot be loaded the size is
  characters / 4, labelled `estimated` everywhere it appears. A downloaded tokenizer is fetched only when
  the user runs a command that needs it, and the first time this is said on screen.
- **Status:** designer's choice.

## D-009: A fixed reference tokenization for token metrics  (2026-11-22)

- **Question:** token precision, recall and IoU (brief §5) need tokens; different embedders tokenize
  differently, which would make the metrics incomparable across the embedder step.
- **Choice:** token metrics use one regular-expression word-and-punctuation tokenization of the source;
  chunk sizes and limits use the embedder's tokens (§4.3). The two are named apart in every output.
- **Status:** designer's choice.

## D-010: Finding text: exact first, then whitespace-insensitive  (2026-11-22)

- **Choice:** chunks and quotes are searched exactly, then with runs of whitespace treated as equal; the
  span covers the original characters. Nothing looser (no case folding, no Unicode normalisation, no
  fuzzy match), so "verbatim" stays verbatim apart from line wrapping.
- **Status:** designer's choice.

## D-011: The split and the intervals  (2026-11-22)

- **Choice:** split by question, 50/50, from a hash of the question id and the seed, stratified by
  document. Intervals: a percentile bootstrap over held-out questions, 2,000 resamples, fixed seed. Ties:
  a paired bootstrap of the per-question difference; "no significant difference" when its 95% interval
  contains 0. No correction for comparing many entries; the leaderboard says the comparison is between
  the top entries. A warning below 30 held-out questions.
- **Why:** questions about the same document are not independent, but splitting by document is
  impossible on small corpora; stratifying by document keeps both splits representative.
- **Status:** awaiting owner review.

## D-012: The closed-book check by code  (2026-11-22)

- **Question:** "drop questions the model answers without the documents" (brief §3), while model judges
  are not in 0.1 (brief §11).
- **Choice:** the model answers with no documents; code drops the question when the answer contains at
  least half of the quote's content words. This is crude (it misses paraphrased answers and can drop a
  question whose quote is made of common words), but it is a rule the user can read and test, not a judge.
- **Status:** awaiting owner review.

## D-013: What counts as a hit  (2026-11-22)

- **Choice:** a hit is a chunk containing the whole quote. Graded measures (nDCG, recall, IoU) use the
  share of the quote's tokens inside each chunk, so a quote split across two retrieved chunks still earns
  recall but no hit, which is the case the chunker blame is for.
- **Status:** designer's choice.

## D-014: Retrieval blame is one stage  (2026-11-22)

- **Question:** the brief's middle rule blames "embedder or retriever".
- **Choice:** one cause, `retrieval`. The fix (§9.3) names the embedder or the retriever when a measured
  alternative recovers the question; telling them apart without such a measurement would be guessing.
- **Status:** awaiting owner review.

## D-015: Rerankers through a `/rerank` route  (2026-11-22)

- **Question:** the OpenAI API has no rerank route.
- **Choice:** the client also speaks the `/rerank` request shape shared by Jina, Cohere, vLLM, llama.cpp
  and Hugging Face TEI; in-process cross-encoders come with the `local` extra. No reranking by asking a
  chat model to score (that is a model judge).
- **Status:** designer's choice.

## D-016: Files, the cache and the configuration  (2026-11-22)

- **Choice:** one working folder, `.ragdoctor/`, git-ignored by the template; the embedding cache in
  SQLite (`sqlite3`, one file, safe across interrupted runs); configuration in an optional
  `ragdoctor.toml` read with `tomllib`; keys only through the environment variable the configuration
  names.
- **Status:** designer's choice.

## D-017: Approving generated code  (2026-11-22)

- **Choice:** doctor's chunker runs only after the user answers `y` to the printed code, or with
  `--approve <sha256>` naming exactly that file (for scripted use after reading it). It runs with
  `python -I` in a subprocess with a temporary working folder, no keys in its environment, a timeout and
  an output limit. Python offers no portable sandbox; the docs say plainly that approval, not the
  subprocess, is the safety step.
- **Status:** awaiting owner review.

## D-018: The user's own stages run in-process  (2026-11-22)

- **Choice:** files in `ragdoctor_stages/` are the user's code, imported like any module they write
  (brief §7). Only model-written code goes through doctor's approval and subprocess.
- **Status:** designer's choice.

## D-019: Plain terminal output; a self-contained HTML file  (2026-11-22)

- **Choice:** `argparse` and plain text tables (no `rich`, no `typer`); the M3 report is one HTML file made
  with string templates from the standard library, inline CSS and a little inline JavaScript, opening
  offline.
- **Status:** designer's choice.

## D-020: Cost needs the user's prices  (2026-11-22)

- **Choice:** ragdoctor ships no price table (prices change and would be wrong); the configuration gives
  a price per million tokens per model. Without one, cost is `unknown`, and the budget can only be in
  minutes. Local models cost 0 when the configuration says so.
- **Status:** designer's choice.

## D-021: Two small commands beyond the brief  (2026-11-22)

- **Choice:** `ragdoctor questions` (make or validate the question set alone, so it can be reviewed
  before spending on a run) and `ragdoctor report` (rebuild the HTML from a results file), plus
  `cache clear`. Each is a thin call into what `rank` already does.
- **Status:** designer's choice; cheap to drop.

## D-022: No PDF in 0.1  (2026-11-22)

- **Choice:** text formats only (Markdown, text, reStructuredText, HTML). PDF extraction changes the text
  (columns, hyphenation, headers), which would make "verbatim" depend on the extractor; a `pdf` extra can
  come with its own change record.
- **Status:** designer's choice.

## D-023: Module names `types` and `io`  (2026-11-22)

- **Choice:** the brief's names are kept (`ragdoctor.types`, `ragdoctor.io`). They shadow standard
  library names only inside the package; absolute imports are the rule, so `import io` still means the
  standard library.
- **Status:** designer's choice.

## D-024: Audit thresholds  (2026-11-22)

- **Choice:** the starting thresholds of design §5.1 (20 tokens for tiny, Jaccard 0.9 on word 5-grams,
  repeated lines in 30% of documents) follow chunkvet's and common practice; every threshold is a named
  setting in `ragdoctor.toml` and printed in the output.
- **Status:** designer's choice; to be revisited with real corpora.

## D-025: User questions need a quote  (2026-11-22)

- **Question:** the brief accepts the user's own questions; scoring needs a gold quote.
- **Choice:** a user question must carry a quote found in the documents (with `document` when the quote
  is ambiguous). User questions are not dropped by the closed-book check: the user chose them.
- **Status:** awaiting owner review.
