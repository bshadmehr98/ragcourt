# Decisions

Smaller choices and the owner's answers. "Owner" entries are the owner's words or choices; the others are
the designer's, open to the owner's review. Code comments refer to entries by number.

## Awaiting owner review

Design 0001 is proposed and was revised after the owner's first answers (2026-11-22). Still open:

| Id | The question | Status |
|---|---|---|
| [D-029](#d-029-milestone-1-includes-the-first-ranking) | Milestone 1 includes the first ranking with local models, not only the audit? | awaiting owner |
| [D-026](#d-026-the-judge-and-its-self-test) | The judge must pass a self-test on labelled cases before its verdicts are used? | awaiting owner |
| [D-027](#d-027-the-default-local-models-come-from-measurement) | Default local models chosen by measurement, `gemma4` on this machine? | awaiting owner |
| [D-011](#d-011-the-split-and-the-intervals) | A 50/50 split by question and a paired bootstrap for ties? | awaiting owner |
| [D-014](#d-014-retrieval-blame-is-one-stage) | Blame `retrieval` as one stage (embedder or retriever)? | awaiting owner |

## The owner's answers (2026-11-22)

| Id | Decision | Who |
|---|---|---|
| D-002 | Python; the owner's toolchain (uv, hatchling, ruff with line length 110 and complexity 10, pyright strict for `src/`, pytest with 90% branch coverage, `scripts/check.sh` as the one gate) and the k8s-holmes workflow adapted (add-stage, real-model-tests, `RAGCOURT_ALLOW_MAIN`). | owner (the brief) |
| D-001 | The name is **ragcourt**: it contains "rag" and is used nowhere else. | owner |
| D-006 | The first version is not model-free: the first useful result uses a model. Any local model that fits the machine may be used. | owner |
| D-007 | Ollama is the local model runtime (installed on the owner's machine). | owner |
| D-012 | A model judge is required. The brief's "not in 0.1: model judges" was wrong. Blame stays code. | owner |
| D-017 | Approval of generated code by answer or exact hash, with "not a sandbox" said plainly: accepted. | owner |
| D-025 | User questions carry a quote and skip the closed-book filter: accepted. | owner |
| D-004 | The repository lives under `bshadmehr98`, its name to follow the product's name. | owner |

## D-001: The name: ragcourt  (2026-11-22)

- **Question:** the brief called the product `ragdoctor`, a working name. It was crowded: `rag-doctor` is
  a published RAG failure-diagnosis tool on PyPI, and two RAG-diagnosis repositories on GitHub are named
  `ragdoctor` and `RagDoctor` ([history/0000-research.md](history/0000-research.md) §3).
- **Owner (2026-11-22):** a name with "rag" that is used nowhere; from the candidates, **ragcourt**.
- **Checked:** `ragcourt` and `rag-court` are free on PyPI, `ragcourt` on npm, no GitHub repository name
  contains it, and a web search for the exact name found no use (research §3, third round). Domains
  and trademarks were not checked.
- **Applied:** package, import and command `ragcourt`; the working folder `.ragcourt/`, the
  configuration `ragcourt.toml`, the user's stages in `ragcourt_stages/`, the base error
  `RagCourtError`, the guard override `RAGCOURT_ALLOW_MAIN`. The owner's brief and the research notes
  keep the old name, as written at the time.
- **Status:** owner's decision.
## D-003: The core is the standard library alone  (2026-11-22)

- **Question:** k8s-holmes allows pydantic in the core. The brief asks for "types (dataclasses, no
  logic)", a first result in under a minute and a codebase read in an evening.
- **Choice:** no core dependencies. Dataclasses for types; `json`, `sqlite3`, `urllib`, `argparse`,
  `tomllib`, `html.parser`, `hashlib`, `random` for the rest. Vectors are lists of floats and cosine is
  plain Python (fast enough to about 200k chunks with a few hundred questions; §18). Every library is an
  extra (design §7.4). `numpy` would speed scoring and may become an optional accelerator later.
- **Status:** designer's choice.

## D-004: Repository URL  (2026-11-22)

- **Owner (2026-11-22):** a repository under `bshadmehr98`, named after the product.
- **Applied:** `https://github.com/bshadmehr98/ragcourt` in `pyproject.toml`; `@bshadmehr98` in
  `CODEOWNERS`. The repository does not exist on GitHub yet; nothing is pushed until the maintainer asks.
- **Status:** owner's answer.
## D-005: No GPU lock script  (2026-11-22)

- **Choice:** the owner's GPU lock script is not copied (k8s-holmes did not have it either). In-process
  local models in the real-model tests may use a GPU; if they share a machine with the owner's other GPU
  work, the test can take the family's lock itself later.
- **Status:** designer's choice.

## D-006: The first minute uses a local model  (2026-11-22)

- **Question:** "a first useful result in under a minute, with no API key" (brief §1).
- **First proposal (rejected by the owner):** `audit`, with no model at all.
- **Owner (2026-11-22):** the first version is not model-free; any local model that fits the machine may
  be used; Ollama is installed.
- **Choice:** the first-minute result is `ragcourt rank <folder>` with nothing configured: it finds
  Ollama on `localhost`, uses the default local models (D-027), writes about 40 questions with quotes,
  filters them with the judge, and ranks the default embedders on the default chunker with blame for
  every miss. `ragcourt setup` (run once, not counted in the minute) checks Ollama, recommends models that
  fit the machine, pulls them after asking, and runs the judge's self-test (D-026). `audit` stays
  model-free when no model is available, and uses the embedder's measured token counts and limit through
  Ollama when it is. The minute is a target to be measured (an end-to-end real-model test on the bundled
  corpus); [history/0002-local-models.md](history/0002-local-models.md) §6 estimates about 60 s on the
  owner's machine before any concurrency.
- **Status:** owner's answer; the shape is the designer's.

## D-007: One client, Ollama first  (2026-11-22)

- **Question:** "local models and any OpenAI-compatible endpoint … through one client" (brief §8).
- **Owner (2026-11-22):** Ollama is the local runtime.
- **Choice:** one `ModelClient` protocol (in `types`) and one HTTP client over `urllib` with two
  dialects: `ollama` (native routes: chat, embed with token counts, show for input limits, pull with the
  user's consent) and `openai` (any OpenAI-compatible endpoint, including llama.cpp, vLLM and LM Studio,
  plus the `/rerank` shape of D-015). With no configuration the client looks for Ollama at
  `http://localhost:11434` and nowhere else. The `local` extra (in-process `sentence-transformers`
  cross-encoders) stays for reranking, which Ollama does not offer.
- **Status:** owner's answer; the shape is the designer's.

## D-008: Token counts: the embedder's own, or labelled estimates  (2026-11-22)

- **Choice:** for an Ollama embedder, sizes come from the token counts Ollama reports when embedding
  (`prompt_eval_count`) and the limit from `/api/show` (both measured in
  [history/0002-local-models.md](history/0002-local-models.md) §3). For other embedders, from their
  tokenizer (`tiktoken:<encoding>` or `hf:<id>`, the `tokens` extra). Otherwise characters / 4,
  labelled `estimated` everywhere it appears.
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

## D-012: The closed-book filter uses a judge  (2026-11-22)

- **Question:** "drop questions the model answers without the documents" (brief §3).
- **First proposal (rejected by the owner):** word overlap by code, because the brief excluded judges.
- **Owner (2026-11-22):** a model judge is required; the brief was wrong to exclude it.
- **Choice:** the answerer gets the question with no documents and is told to reply `UNKNOWN` when it does
  not know; an `UNKNOWN` keeps the question without asking the judge (code); otherwise the judge grades
  the answer against the quote with a strict rubric and gives a reason, and a correct answer drops the
  question. A second judge call checks validity (a real question, answered by the quote). Every verdict,
  its reason, the judge's model and the prompt version are stored with the question. Judges filter
  questions and (as a stage) may rerank; they never decide blame or any metric.
- **Status:** owner's answer; the shape is the designer's.

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

## D-015: Rerankers  (2026-11-22)

- **Question:** the OpenAI API has no rerank route, and Ollama 0.34.4 has none either (measured,
  [history/0002-local-models.md](history/0002-local-models.md) §7).
- **Choice:** three rerankers: `llm` (a chat model orders the top 20 candidates in one listwise call; local
  through Ollama), `endpoint` (the `/rerank` shape shared by Jina, Cohere, vLLM, llama.cpp and TEI) and
  `cross-encoder` (in-process, the `local` extra). Now that judges are allowed (D-012), a chat model may
  rank; it still never decides blame.
- **Status:** designer's choice.

## D-016: Files, the cache and the configuration  (2026-11-22)

- **Choice:** one working folder, `.ragcourt/`, git-ignored by the template; the embedding cache in
  SQLite (`sqlite3`, one file, safe across interrupted runs); configuration in an optional
  `ragcourt.toml` read with `tomllib`; keys only through the environment variable the configuration
  names.
- **Status:** designer's choice.

## D-017: Approving generated code  (2026-11-22)

- **Choice:** doctor's chunker runs only after the user answers `y` to the printed code, or with
  `--approve <sha256>` naming exactly that file (for scripted use after reading it). It runs with
  `python -I` in a subprocess with a temporary working folder, no keys in its environment, a timeout and
  an output limit. Python offers no portable sandbox; the docs say plainly that approval, not the
  subprocess, is the safety step.
- **Status:** accepted by the owner (2026-11-22).

## D-018: The user's own stages run in-process  (2026-11-22)

- **Choice:** files in `ragcourt_stages/` are the user's code, imported like any module they write
  (brief §7). Only model-written code goes through doctor's approval and subprocess.
- **Status:** designer's choice.

## D-019: Plain terminal output; a self-contained HTML file  (2026-11-22)

- **Choice:** `argparse` and plain text tables (no `rich`, no `typer`); the M3 report is one HTML file made
  with string templates from the standard library, inline CSS and a little inline JavaScript, opening
  offline.
- **Status:** designer's choice.

## D-020: Cost needs the user's prices  (2026-11-22)

- **Choice:** ragcourt ships no price table (prices change and would be wrong); the configuration gives
  a price per million tokens per model. Without one, cost is `unknown`, and the budget can only be in
  minutes. Local models cost 0 when the configuration says so.
- **Status:** designer's choice.

## D-021: Small commands beyond the brief  (2026-11-22)

- **Choice:** `ragcourt setup` (find Ollama, recommend and pull models after asking, test the judge;
  D-006), `ragcourt questions` (make or validate the question set alone, so it can be reviewed before
  spending on a run) and `ragcourt report` (rebuild the HTML from a results file), plus `cache clear`. Each is a thin call into what `rank` already does.
- **Status:** designer's choice; cheap to drop.

## D-022: No PDF in 0.1  (2026-11-22)

- **Choice:** text formats only (Markdown, text, reStructuredText, HTML). PDF extraction changes the text
  (columns, hyphenation, headers), which would make "verbatim" depend on the extractor; a `pdf` extra can
  come with its own change record.
- **Status:** designer's choice.

## D-023: Module names `types` and `io`  (2026-11-22)

- **Choice:** the brief's names are kept (`ragcourt.types`, `ragcourt.io`). They shadow standard
  library names only inside the package; absolute imports are the rule, so `import io` still means the
  standard library.
- **Status:** designer's choice.

## D-024: Audit thresholds  (2026-11-22)

- **Choice:** the starting thresholds of design §5.1 (20 tokens for tiny, Jaccard 0.9 on word 5-grams,
  repeated lines in 30% of documents) follow chunkvet's and common practice; every threshold is a named
  setting in `ragcourt.toml` and printed in the output.
- **Status:** designer's choice; to be revisited with real corpora.

## D-025: User questions need a quote  (2026-11-22)

- **Question:** the brief accepts the user's own questions; scoring needs a gold quote.
- **Choice:** a user question must carry a quote found in the documents (with `document` when the quote
  is ambiguous). User questions are not dropped by the closed-book check: the user chose them.
- **Status:** accepted by the owner (2026-11-22).

## D-026: The judge and its self-test  (2026-11-22)

- **Question:** small local models grade a refusal as a correct answer
  ([history/0002-local-models.md](history/0002-local-models.md) §5); unchecked, such a judge keeps
  questions the model can answer from memory and drops good ones.
- **Choice:** a bundled set of about 40 labelled cases (closed-book answers that are correct, wrong,
  generic, refusals and `UNKNOWN`; valid and invalid questions). Before a model is used as judge,
  `setup` (and the first run with a new judge) grades the set; below 90% agreement the model is refused
  as judge with its errors shown, and the user picks another. The result is cached per model and prompt
  version and printed in every run's output.
- **Status:** awaiting owner review.

## D-027: The default local models come from measurement  (2026-11-22)

- **Choice:** `setup` recommends models by what fits the machine (VRAM and RAM as Ollama reports them),
  from a small table kept in the code and justified by measurements like
  [history/0002-local-models.md](history/0002-local-models.md). On the owner's machine (8 GB VRAM):
  `gemma4` as question writer and judge (19 of 20 quotes verbatim, sensible strict verdicts),
  `nomic-embed-text`, `embeddinggemma` and `mxbai-embed-large` as the quick embedders, and `bge-m3`,
  `all-minilm` and `qwen3-embedding:0.6b` added in the full search. Any Ollama model can be named instead;
  the judge self-test still applies.
- **Status:** awaiting owner review.

## D-028: Question rules by code before the judge  (2026-11-22)

- **Choice:** cheap code rules drop what the measurement showed is common, before any judge call: a quote
  of fewer than 6 words or with no sentence (a bare name or a code line), a question of fewer than 3
  words for `paraphrase`, a missing or unknown `style`. Each drop is counted by reason.
- **Status:** designer's choice; thresholds in `ragcourt.toml`.

## D-029: Milestone 1 includes the first ranking  (2026-11-22)

- **Question:** the brief's milestones put the audit alone in M1; the owner does not want the first
  version to be model-free.
- **Choice:** M1 delivers the audit and the first-minute ranking (Ollama client, `setup`, questions with
  the judge, the default embedders on the default chunker, metrics with intervals, blame). M2 completes
  the search (all four stages, greedy order, budget, fixes, `explain`, extras).
- **Status:** awaiting owner review.
