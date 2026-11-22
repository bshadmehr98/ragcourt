Set this repository up in the shape of my other projects, then design the product in the brief below.
Do not write product code until I accept the design.

## Step 1: the shape

Clone https://github.com/bshadmehr98/k8s-holmes into a temporary folder outside this repository and
read it fully: CLAUDE.md, AGENTS.md, CONTRIBUTING.md, CHANGELOG.md, .claude/ (settings.json, every
skill, hook and agent), .github/, design/, scripts/check.sh, pyproject.toml. For how examples and docs
are organised, also read https://github.com/honeworks/hone-flow (examples/ and docs/).

Recreate that structure here, adapted to this product, not copied blindly:
- Same toolchain: uv, hatchling, ruff (line length 110, complexity 10), pyright strict for src/,
  pytest with 90% branch coverage, scripts/check.sh as the one gate.
- Same flow and skills. Replace add-adapter with add-stage (a chunker, embedder, retriever or
  reranker) and real-cluster-tests with real-model-tests. Remove everything Kubernetes-specific from
  settings.json, the skills, the agents and the rules. Rename the guard override variable.
- Same design/ folder: README.md, current.md with numbered guarantees and an "implemented" section,
  changes/, decisions.md, history/.
- CHANGELOG.md in Keep a Changelog format, starting with [Unreleased].
- Save this whole message word for word as design/history/0001-owner-brief.md.
- Write design/history/0000-research.md: search for existing tools (AutoRAG, rag-forge, chunk-bench,
  chunkvet, MTCB, Chroma chunking_evaluation, Chonkie, Ragas and any you find), mark each statement
  `sourced` or `inferred`, and say what is still unresearched. Check the name for clashes on PyPI and
  GitHub and raise it as D-001.

## Step 2: the brief

Build **ragdoctor** (working name), an open-source Python command-line tool for RAG developers.

One sentence: rank chunkers, embedding models, retrievers and rerankers on the user's own documents,
and say which stage caused each miss.

### 1. Goals
- A developer gets a first useful result in under a minute, with no API key.
- Results are numbers measured on their documents, not general advice.
- Every failed question has one named cause and a suggested fix.
- A newcomer can read the whole codebase in an evening and add a stage in one file.

### 2. Commands
- `audit`: no model needed. Chunk the documents and flag chunks cut mid-sentence, chunks with no
  heading context, split tables and code blocks, repeated headers and footers, near-duplicates, tiny
  chunks, and chunks longer than the embedding model's input limit. Show boundaries on the source text.
- `rank`: a leaderboard per stage and the best overall pipeline.
- `explain`: for each failed question, the cause and what would fix it.
- `doctor`: a model reads sample documents, describes their structure, recommends chunkers, and may
  write a custom chunker file. Show the code and ask before running it; run it in a subprocess with a
  timeout; validate its output; then rank it against the baselines. A suggestion is never reported as
  better without the measurement.

### 3. Questions and gold answers
A model writes each question together with an exact quote from the source that answers it. If the
quote is not found verbatim in the source, the question is dropped. Gold answers never depend on any
chunking. Include paraphrased and keyword-style questions, drop questions the model answers without
the documents, and accept the user's own questions. Search on a dev split; report on a held-out split.

### 4. Blame
Computed by code, never by a model. For each miss: the quote is intact in no chunk (chunker); the
chunk exists but is outside the top 50 (embedder or retriever); it is in the top 50 but below k
(ranking). Report each stage's ceiling.

### 5. Metrics
Hit@k, MRR, nDCG, Recall@k; token precision, recall and IoU against the gold quote; recall within a
fixed token budget, so large chunks cannot win by size; vectors, tokens per query, latency and cost.
Report confidence intervals and say "no significant difference" when the top results are tied. Chunk
sizes are measured in the embedder's own tokens and reported as measured.

### 6. Search
Greedy by stage, embedders first, not a full grid. Embeddings are cached by content and model. Print
an estimate of time and cost before a run and respect a budget.

### 7. Stages and extension
Four stage kinds, each registered with a decorator, one file per implementation, loaded also from a
folder in the user's project. A chunker is a function from text to a list of strings; the tool finds
the offsets. Ship a few native chunkers and thin adapters for existing libraries as optional extras.

### 8. Models
Local models and any OpenAI-compatible endpoint, for chat and embeddings, through one client. Nothing
leaves the machine unless the user configures an endpoint. No telemetry.

### 9. Code structure
Layers that import only downward: types (dataclasses, no logic) → stages → core (pure functions:
pipeline, metrics, blame, search, audit) and io (loaders, model client, cache, questions, report) →
commands (one file each) → cli. Stages never import each other; only the pipeline joins them. Enforce
the import rule in scripts/check.sh. Keep the template's "Keep it simple" limits.

### 10. Tests, docs, examples
The default suite is offline and deterministic: a fake embedder, a scripted model, a small bundled
corpus. Real models only in marked tests. One small runnable example per concept, in reading order,
executed by tests. A docs page that follows one question from document to blame.

### 11. Not in 0.1
Answer generation, model judges, vector databases, images, audio, video, a hosted service.

## Step 3: stop

Write design/changes/0001-initial-design.md (status `proposed`) and design/current.md from this
brief, with milestones: M1 audit, M2 rank and explain, M3 the HTML report, M4 doctor. Put your own
choices in design/decisions.md as D- entries. Commit in small Conventional Commits, do not push, and
stop. Give me the decision, the open questions and the file paths, and wait for my approval.
