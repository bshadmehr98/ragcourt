# Decisions

Smaller choices and the owner's answers. "Owner" entries are the owner's words or choices; the others are
the designer's, open to the owner's review. Code comments refer to entries by number.

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
| D-029 | Milestone 1 is the whole project (0.1), not a part of it. | owner |
| D-026 | The judge's self-test is accepted, and it must be explained to the user (D-030). | owner |
| D-030 | Nothing happens blindly: a new user must know what is being judged, how, by which model, and why. | owner |
| D-027 | The default local models are accepted; the user must be able to change them easily (D-031). | owner |
| D-011 | Choosing on some questions and reporting on others is accepted; but one mixed set of a few dozen is not enough: many questions of each kind are needed (D-032). | owner |
| D-034 | No first answer in one minute: about 540 questions taking 15 to 25 minutes once is fine. | owner |
| D-016 | No database; nothing that complicates the code. | owner |
| D-014 | "retrieval" as one blame stage is not good enough: why a miss happened is the reason to use the product, so blame must be precise (D-033). | owner |
| D-032, D-033, D-035, D-036 | Accepted with design 0001: six question categories, 90 each; blame as a stage and a mechanism; progress and resume; the simplicity rules and the small-module layout. | owner |

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

## D-006: The first result uses a local model; no one-minute target  (2026-11-22)

- **Question:** "a first useful result in under a minute, with no API key" (brief §1).
- **First proposal (rejected):** `audit`, with no model at all.
- **Owner (2026-11-22):** the first version is not model-free; any local model that fits the machine may
  be used; Ollama is installed. Later the same day: drop the one-minute target (D-034).
- **Choice:** `ragcourt setup` once (checks Ollama, recommends models that fit, pulls after asking, tests
  the judge), then `ragcourt rank <folder>`: the full set of questions and the search, with the plan and
  its time shown before it starts and progress while it runs (D-035). `audit` gives a useful result in
  seconds meanwhile, with token counts measured through Ollama when it is running.
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
  tokenizer (`tiktoken:<encoding>`, the `tokens` extra; `hf:<id>` was planned and dropped, D-058). Otherwise characters / 4,
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

## D-011: Choosing on one half of the questions, reporting on the other  (2026-11-22)

- **In plain words:** ragcourt tries several options (say five embedding models) and picks the best. If it
  picked the winner and reported its score on the same questions, the score would be flattered: some of
  the winner's lead is luck on those particular questions. So the questions are split in two, like
  practice questions and the real exam: the **dev** half is used to choose, the **held-out** half only to
  report. With 40 questions, 20 choose and 20 report.
- **Ties:** with 20 questions, 70% against 65% may be luck. ragcourt estimates the noise by re-drawing
  the questions many times (a bootstrap, 2,000 times with a fixed seed) and looking at how the
  difference between the top two moves; if "no difference" is within that range it prints "no
  significant difference" and does not crown a winner. It compares the two options on the same questions
  (paired), which separates them better than comparing two averages.
- **The choices behind it:** half and half (`--holdout 0.5`), questions assigned to a half by a fixed hash,
  each document's questions spread over both halves; a 95% range; a warning when fewer than 30 questions
  are left for reporting, because the ranges get wide.
- **The alternative:** report on all questions and accept a flattered score; simpler, but the brief asks
  for the split (brief §3).
- **Owner (2026-11-22):** accepted, with a condition: "for deciding if a specific embedding acts better
  we need different kinds of questions", for example 60 with different wording, 60 misleading, 60 with
  specific words, "so only using 60 questions is not good enough at all". See D-032: the split is now one
  third to choose and two thirds to report, within each category.
- **Status:** owner's answer.

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

- **In plain words:** when a question is missed, ragcourt names one cause. Two are clear: the answer was
  cut in half by the chunker (`chunker`), or the right chunk was found but ranked too low to be shown
  (`ranking`). The third case is when the right chunk exists but the search did not bring it into the top
  50. Two things work together there: the **embedding model** (turns text into vectors) and the
  **retriever** (the search method: vectors, keywords, or both). From one run ragcourt cannot tell which
  of the two failed.
- **Choice:** call that cause `retrieval`, and be specific only when a measurement says so: if, during the
  search, another embedding model found the chunk, the fix names that model; if keyword or hybrid search
  found it, the fix names that retriever; if nothing tested found it, the fix says so.
- **The alternative:** always split it into "embedder" and "retriever", which would mean guessing.
- **Owner (2026-11-22):** not good enough: these failures are exactly why a user would use the product.
  Replaced by D-033.
- **Status:** superseded by D-033.

## D-015: Rerankers  (2026-11-22)

- **Question:** the OpenAI API has no rerank route, and Ollama 0.34.4 has none either (measured,
  [history/0002-local-models.md](history/0002-local-models.md) §7).
- **Choice:** three rerankers: `llm` (a chat model orders the top 20 candidates in one listwise call; local
  through Ollama), `endpoint` (the `/rerank` shape shared by Jina, Cohere, vLLM, llama.cpp and TEI) and
  `cross-encoder` (in-process, the `local` extra). Now that judges are allowed (D-012), a chat model may
  rank; it still never decides blame.
- **Status:** designer's choice.

## D-016: Plain files, no database  (2026-11-22)

- **Owner (2026-11-22):** no database, nothing that complicates things.
- **Choice:** everything ragcourt keeps is a plain file in `.ragcourt/`: the question file (JSONL), the
  results (JSON), progress (JSONL), the judge's self-test results (JSON), and the embedding cache as one
  folder per model with `keys.txt` and `vectors.f32`, appended to and read whole into a dictionary
  (design §10.2). The first proposal's SQLite cache is dropped. Configuration is one optional
  `ragcourt.toml` read with `tomllib`; keys only through the environment variable it names.
- **Why it is enough:** a cache of 100,000 vectors of 1,024 dimensions is 400 MB of float32 and loads in
  seconds; corpora larger than that are past 0.1's limits (design §18).
- **Status:** owner's requirement; the shape is the designer's.

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

- **Replaced 2026-11-24** by [changes/0005](changes/0005-pdf.md) and D-059: PDF is read with the extra `pdf`.
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
- **Owner (2026-11-22):** accepted; it must be explained to the user, case by case (D-030).
- **Status:** owner's answer.

## D-027: The default local models come from measurement  (2026-11-22)

- **Choice:** `setup` recommends models by what fits the machine (VRAM and RAM as Ollama reports them),
  from a small table kept in the code and justified by measurements like
  [history/0002-local-models.md](history/0002-local-models.md). On the owner's machine (8 GB VRAM):
  `gemma4` as question writer and judge (19 of 20 quotes verbatim, sensible strict verdicts),
  `nomic-embed-text`, `embeddinggemma` and `mxbai-embed-large` as the quick embedders, and `bge-m3`,
  `all-minilm` and `qwen3-embedding:0.6b` added in the full search. Any Ollama model can be named instead;
  the judge self-test still applies.
- **Owner (2026-11-22):** accepted; the user must be able to change them easily (D-031).
- **Status:** owner's answer.

## D-028: Question rules by code before the judge  (2026-11-22)

- **Choice:** cheap code rules drop what the measurement showed is common, before any judge call: a quote
  of fewer than 6 words or with no sentence (a bare name or a code line), a question of fewer than 3
  words for `paraphrase`, a missing or unknown `style`. Each drop is counted by reason.
- **Status:** designer's choice; thresholds in `ragcourt.toml`.

## D-029: Milestone 1 is the whole project  (2026-11-22)

- **Question:** the brief split 0.1 into four milestones (audit; rank and explain; the HTML report;
  doctor); the first revision moved the first ranking into milestone 1.
- **Owner (2026-11-22):** milestone 1 is the full project.
- **Choice:** one milestone, built on one branch in the order of the change record (each step tested and
  committed, reviewed by the reviewer agents at the end), shown to the owner once, when all 30 guarantees
  pass.
- **Status:** owner's answer.

## D-030: Nothing happens blindly  (2026-11-22)

- **Owner (2026-11-22):** "Imagine a new user using this product. Nothing should happen blindly." The
  user calling ragcourt must know what is being judged, how, and by which model.
- **Choice:** before any model call, a plan in plain words (each step, its role, its model and where that
  choice came from, what the model is shown and returns, the estimate). Before the first judge call, a
  paragraph on what the judge is asked and shown and what it never decides. Every prompt and the judge's
  labelled cases are readable files (`ragcourt prompts show`). The self-test is shown case by case. Every
  verdict keeps its reason (`ragcourt questions show`). Leaderboards and blame lists end with a legend of
  their words and rules. `docs/judge.md` and `docs/models.md` explain it with real output (design §6.6,
  §10.3, §11.4, §13.2; guarantees 28 to 30).
- **Status:** owner's requirement; the shape is the designer's.

## D-031: Changing a model is one command  (2026-11-22)

- **Owner (2026-11-22):** the defaults are fine, but the user must be able to configure them easily.
- **Choice:** five named roles (`writer`, `judge`, `embedders`, `reranker`, `doctor`); `ragcourt models`
  shows them with where each came from; `ragcourt models set <role> <model>` writes `ragcourt.toml` and,
  for a judge, runs the self-test; per-run flags override; `setup` writes a commented `ragcourt.toml`.
  Precedence: flag, file, default, printed in the plan (design §11.4).
- **Status:** designer's choice.

## D-032: Questions by category, 90 each  (2026-11-22)

- **Owner (2026-11-22):** many questions of each kind, because embedders fail on specific kinds.
- **Choice:** six categories, each aimed at a known weakness: `paraphrase` (different wording),
  `keyword` (search terms), `exact_term` (a rare identifier, name or number), `distractor` (worded like a
  similar passage that does not answer it: the misleading questions), `negation`, `numeric`; plus the
  user's own (design §6.7). 90 per category by default, 30 to choose and 60 to report; every result per
  category and overall (the mean of categories, so each counts the same); a category under 30 reported
  questions is "too few to rank"; each category prints the smallest difference it can tell apart (§6.8).
- **Why these checks:** a local model asked for a negation, a number or a misleading question wrote one
  that was really of that kind only 1 to 3 times in 8 ([history/0003-question-categories.md](history/0003-question-categories.md)).
  So passages that can support a category are chosen by code, membership is checked by code (and by the
  judge for `negation` and `distractor`), and failures are dropped and counted, never kept as "hard".
- **Cost:** about 540 questions, 15 to 25 minutes on the owner's machine once per corpus (`inferred`),
  shown in the plan before it starts; the counts and categories are settings.
- **Not in 0.1:** questions that need two passages (multi-hop), and unanswerable questions; both need a
  different gold than one quote.
- **Status:** accepted by the owner (2026-11-22).

## D-033: Blame: a stage, a mechanism, evidence and a level  (2026-11-22)

- **Owner (2026-11-22):** "Can't we have a better system? These are the reasons a user may actually use
  our project."
- **Choice:** four stages (`chunker`, `embedder`, `retriever`, `ranking`) and fourteen mechanisms, checked
  by code in a fixed order so each miss gets one cause and a list of anything else also seen (design
  §9.1). Examples: the quote was cut across a boundary (`chunker.split`); it lay past the embedder's input
  limit, so the embedder never read it (`chunker.over_limit`); it was drowned in a long chunk, shown by
  embedding the quote alone (`chunker.diluted`); keyword search found it and the embedder did not
  (`embedder.exact_words`); a similar passage that does not answer took its place (`embedder.distracted`);
  the reranker pushed it out (`ranking.reranker_demoted`).
- **How it tells the embedder from the retriever:** a few cheap probes per question (§9.4): the quote
  embedded alone, BM25's rank of the right chunk whatever the retriever, every measured embedder's rank,
  ranks before and after the reranker and in each half of a hybrid search, the quote's token position.
- **Evidence level:** `confirmed` when a configuration measured in the run, differing only in the blamed
  stage, gets the question right; otherwise `indicated`, with the command that would confirm it. The share
  of confirmed blames is printed (§9.3, §9.5).
- **Still never a model:** every check is arithmetic on spans, ranks and scores.
- **Status:** accepted by the owner (2026-11-22).

## D-034: No first answer in one minute  (2026-11-22)

- **Question:** the brief's one-minute first result against the ~540 questions a trustworthy ranking
  needs (D-032).
- **First proposal:** a labelled "first look" of 8 questions per category.
- **Owner (2026-11-22):** writing 540 questions taking time is fine; drop the one-minute answer. The
  designer agreed: a ranking on a handful of questions per category is noise that people would act on.
- **Reopened 2026-11-24** by the owner ([changes/0004](changes/0004-quick-look.md)): `rank --quick` exists,
  and by the too-few rule it never names a winner.
- **Result:** no quick mode, no first-minute test; one `rank`, with the plan and time shown first, visible
  progress and resume (D-035). Guarantee 26 now tests progress and resume.
- **Status:** owner's answer.

## D-035: Progress and resume  (2026-11-22)

- **Question:** a full run takes 15 to 25 minutes on the owner's machine; over that time a laptop may
  sleep, a model may fail, the user may press Ctrl-C.
- **Choice:** progress lines while it runs (per step; per category while questions are written; time
  left), kept in `progress.jsonl`; every finished unit (question, embedding, evaluated configuration)
  written as it finishes, so `rank --resume` continues where it stopped and gives the same results as an
  uninterrupted run (design §10.4, guarantee 26).
- **Status:** accepted by the owner (2026-11-22).

## D-036: Simple code, small modules, plain files  (2026-11-22)

- **Owner (2026-11-22):** the code must not be complicated, yet maintainable, easy to understand and easy
  to extend: no database, small modules rather than big files, no hard-to-read code such as complex
  comprehensions; these rules belong in the project's skills and instructions.
- **Choice:**
  - the rules in CONTRIBUTING.md "Keep it simple", in three parts: what we build with (the standard
    library, plain files, sequential code, functions and frozen dataclasses, no magic), how code is
    shaped (one concept per module, short flat functions, readable expressions, explicit state, names
    that say what) and how it grows (every extension is one new file and maybe one line in a list);
  - the limits checked in the gate: modules ≤ 250 lines, functions ≤ 40 lines, ≤ 3 nested blocks,
    complexity ≤ 10, ≤ 6 parameters with booleans keyword-only, comprehensions with one `for` and at most
    one `if` and none nested, no nested conditional expressions, walrus, `global`, `eval` or metaclasses,
    inheritance only for protocols, enums and errors, no junk-drawer module names;
    `scripts/check_simple.py` checks what ruff cannot, and ruff gains rules for blind excepts, prints,
    commented-out code, unused arguments, boolean flags, pathlib and docstrings;
  - the `keep-it-simple` skill as the working checklist, including how to fix a failed check without
    gaming it; AGENTS.md rule 1, CLAUDE.md, the other skills and the simplicity reviewer point to it;
  - the module layout of design §3.2: one file per stage, audit check, question category, blame stage and
    command, with the package's `__init__.py` holding the ordered list.
- **Kept from the brief:** complexity 10 (brief §9 and the toolchain); the line length of 110.
- **Status:** accepted by the owner (2026-11-22).

## D-037: One copy of the bundled corpus, in the package  (2026-11-22)

- **Question:** design §15.2 had the corpus in `tests/fixtures/corpus/` and "also shipped as
  `ragcourt.testing.corpus`": two copies that could drift apart.
- **Choice:** one copy in `src/ragcourt/testing/corpus/`, found with `ragcourt.testing.corpus_path()`, so
  tests, examples and users trying ragcourt read the same files. `tests/fixtures/` keeps the other saved
  fixtures (old file versions, recorded model replies). The documents describe a made-up job queue,
  Larkspur, so no real product's text is copied.
- **Status:** designer's choice.

## D-038: `HTMLParser` is the one allowed base class outside protocols, enums and errors  (2026-11-22)

- **Question:** HTML files are read with the standard library (design §4.1), and `html.parser` works only
  by subclassing `HTMLParser`; the simplicity rules allowed no inheritance beyond protocols, enums and
  errors (D-036).
- **Choice:** allow `HTMLParser` by name in `scripts/check_simple.py` and in CONTRIBUTING.md, used once in
  `io/html_text.py`. Any further base class needs its own entry here.
- **Status:** designer's choice.

## D-039: An unknown key in `ragcourt.toml` is an error  (2026-11-22)

- **Question:** what to do with a key ragcourt does not know, such as a misspelled `stage_dir`.
- **Choice:** stop with a message that names the unknown key and lists every known one with what it does.
  A typo that is silently ignored would run with a setting the user believes is off (D-030: nothing
  happens blindly). Each step of the milestone adds its settings to the one list in `io/config.py`.
- **Status:** designer's choice.

## D-040: Reading real documents  (2026-11-22)

- **Found** by loading real corpora (design/history/0004-real-data.md) and by the step-1 reviews:
  HTML pages of real sites are mostly menus (the Python docs, Wikipedia); HTML may leave out `</tr>`,
  `</td>` and `</head>`, and the first version dropped whole tables or the whole body when it did; a
  byte-order mark hid a file's first heading; one unreadable file stopped the whole load.
- **Choice:** keep only the main content when a page marks it (`<main>`, `role="main"`) and always drop
  `<nav>` and `<aside>`; close implied end tags as a browser does; inside a table everything is cell
  text; drop a leading byte-order mark; skip and report unreadable files and links to folders; refuse a
  single file of another kind. Site-specific clutter that is not marked (Wikipedia's language list) is
  left for the audit's `boilerplate.repeated` check.
- **Status:** designer's choice.

## D-041: Ollama embeddings: one text per call, the limit in force measured  (2026-11-22)

- **Measured** on Ollama 0.34.4 (design/history/0004-real-data.md): `/api/embed` returns one
  `prompt_eval_count` for the whole call (4 + 8 tokens gave 12), so per-text counts need one text per
  call, and that was no slower (nomic 98 vs 95 texts/s, mxbai 52 vs 49, bge-m3 40 vs 42). Inputs over the
  limit are cut silently by default (`truncate: false` gives HTTP 400). The limit in force is the
  smallest of the model's context length, `num_ctx` and `num_batch`: `bge-m3` cut at 2,048 of its 8,192
  until `num_batch` was raised; `all-minilm` cut at 256 of 512.
- **Choice:** an embedder returns token counts with its vectors (`Embedded`); the `ollama` embedder sends
  one text per call with `num_ctx` and `num_batch` set to the context length, and measures the limit in
  force once per model with an over-long probe (its count is the limit). Design §4.3, §7.1 and §11.1 are
  updated. Open for step 3: how a stage receives the client (a factory parameter), and the client's other
  routes (`/api/show`, `/api/tags`, `/api/pull`, `/rerank`), seed and temperature in `ChatRequest`.
- **Status:** designer's choice, from measurement.

## D-042: Query and document prefixes  (2026-11-22)

- **Question:** several embedding models document different prefixes for questions and for passages
  (`nomic-embed-text`: `search_query:` / `search_document:`; `mxbai-embed-large`: an instruction before
  queries; `embeddinggemma`: task prompts). An embedder that cannot tell a question from a chunk cannot
  use them.
- **Measured** on Chroma's chunking-evaluation questions (hit@5 over 800-character chunks): with and
  without the documented prefixes, nomic 57 vs 58 of 62 and 106 vs 107 of 116, mxbai 62 vs 62 and 92 vs
  95, embeddinggemma 62 vs 62 and 109 vs 105. The effect is small and goes both ways, which is a reason to
  measure it on the user's documents rather than assume it.
- **Choice:** `Embedder.embed(texts, *, as_query=False)`; the `ollama` embedder takes `query_prefix` and
  `document_prefix` parameters, with each known model's documented prefixes as its defaults, shown in the
  plan (D-030); the cache keys on the exact text sent, prefix included.
- **Status:** designer's choice.

## D-043: Chunk sizes in reference tokens; the units at layer 0  (2026-11-22)

- **Question:** the native chunkers need a tokenizer, but stages (layer 1) cannot import `core`.
- **Choice:** `ragcourt/text_units.py` at layer 0 holds the reference tokenization (words and punctuation)
  and the sentence rules; the native chunkers' `size` is in those tokens, the same for every embedder.
  The audit reports sizes in the embedder's own tokens.
- **Status:** designer's choice.

## D-044: Near-duplicates by exact shingles, found through an index  (2026-11-22)

- **Choice:** `duplicate.near` compares word 5-gram sets exactly, finding candidates through the 5-grams
  they share, at any corpus size; the MinHash of design §5.1 is not needed at 0.1's scale.
- **Status:** designer's choice.

## D-045: A `flows` layer between core and io, and commands  (2026-11-22)

- **Question:** `rank`, `questions` and `doctor` share building the question set, evaluating pipelines
  and the judge's self-test; commands may not import each other, and `core` and `io` may not either.
- **Choice:** `ragcourt/flows/` (layer 3) holds those shared parts; commands (layer 4) and the cli
  (layer 5) sit above. A flow prints nothing; it reports through a `say` function the command gives it.
- **Status:** designer's choice.

## D-046: Machine memory from the OS and nvidia-smi  (2026-11-22)

- **Question:** Ollama has no route that reports a GPU's total memory (design §11.3 assumed one).
- **Choice:** RAM from the OS, GPU memory from `nvidia-smi` when present, else unknown and said so.
- **Status:** designer's choice.

## D-047: When the question set is reused, resumed or written afresh  (2026-11-22)

- **Choice:** reused when the documents, writer, judge, prompts, seed, categories and count are the same
  and the set is complete; resumed (skipping every passage already tried, kept or dropped) when it is
  unfinished or the count grew; revalidated (quotes found again) when only the documents changed; written
  afresh when the writer, judge, prompts, seed or categories changed. Dropped questions go to
  `questions.dropped.jsonl` with every verdict, for `questions show --dropped`.
- **Status:** designer's choice.

## D-048: Distractor questions as measured with a local model  (2026-11-22)

- **Found** (design/history/0004 and the real runs): `gemma4` rarely words a question "like the other
  passage"; the code check then dropped all of them, and the judge, asked "yes only if the other passage
  does not answer", answered the double negation backwards.
- **Choice:** the writer is given the twin's own words and must use two of them (the code check); the judge
  is asked plainly whether the other passage answers, and the question passes on "no"; twins more alike
  than 0.5 (near-duplicates, which answer the same) are not offered; paragraphs repeated across documents
  (headers, footers) are never offered to the writer; numeric quotes may state the number in words.
- **Status:** designer's choice, from measurement.

## D-049: A keyword search is a valid question  (2026-11-22)

- **Found:** `gemma4` as judge called the self-test's keyword-search case invalid.
- **Choice:** the validity prompt says a short keyword search counts as a real question. The judge's score
  went from 95% to 98%.
- **Status:** designer's choice, from measurement.

## D-050: The dev choice explained  (2026-11-22)

- **Choice:** each step's chosen entry says when it was tied on dev and was kept for being cheaper, then
  smaller, then first listed, and warns when dev and held-out questions disagree. A BM25 pipeline's label
  shows no embedder.
- **Status:** designer's choice.

## D-051: Measured counts at the limit; the limit kept  (2026-11-22)

- **Choice:** a count Ollama reports can only reach the limit (it counts what it read), so a measured
  count at the limit is a chunk that was cut (`size.over_limit`). Each Ollama model's measured limit is
  kept per model version in `.ragcourt/cache/limits.json`, so a second run makes no embedding call.
- **Status:** designer's choice.

## D-052: When rank asks before starting  (2026-11-22)

- **Choice:** the plan is always printed; the project's first run, and any run estimated over a minute,
  asks before starting; without a terminal the answer is no and `--yes` starts it. The money budget
  (`--budget-usd`, `[budget] usd`) refuses a run whose endpoint embeddings would cost more, or whose cost is
  unknown; the time budget is checked before each step.
- **Status:** designer's choice.

## D-053: The gate installs every extra but `local`  (2026-11-22)

- **Choice:** `sentence-transformers` brings torch (gigabytes), so `scripts/check.sh` and CI install
  every extra but `local`; its adapters are tested for the missing-extra message by default and by hand
  otherwise.
- **Status:** designer's choice.

## D-054: `chonkie.semantic` left out of 0.1  (2026-11-22)

- **Choice:** it downloads its own embedding model on first use, which would break "no download without
  your yes" (design §11.3); the token, sentence and recursive adapters are kept.
- **Status:** designer's choice.

## D-055: Chunker specs are separated by `;` on the command line  (2026-11-22)

- **Choice:** a spec holds commas (`recursive:size=256,overlap=32`), so `--chunkers` separates specs with
  `;`; other lists use commas.
- **Status:** designer's choice.

## D-056: What the review of milestone 1 changed  (2026-11-22)

- **Found** by two independent reviews of the built code and its tests, each confirmed by running it: a
  torn write could shift the embedding cache by one vector; a run stopped by the budget could not be
  resumed; saved measurements were reused for another question set; an empty corpus or too few questions
  gave a confident report; with no dev questions the choice was made on held-out ones; categories of equal
  size were resampled in step; BM25 returned unmatched chunks; a server without token counts gave zeros
  labelled measured; a torn question line broke later runs; a quote found twice in one document was
  accepted; every category "too few" still named a winner.
- **Choice:** all fixed and tested. The cache trims both files to the rows they share; the budget writes
  `partial.json` and `--resume` continues; a saved measurement is reused only for the same questions;
  `rank` refuses no documents, and question sets without both dev and held-out questions (every category
  of two or more questions gets a dev question); each category has its own resample seed; BM25 returns
  only chunks that share a word; missing counts are unknown; damaged lines are named and a torn last line
  skipped; a quote twice in a document is ambiguous; when every category is too few the board is
  "indicative" and names no winner; `rank` says when an unfinished run could be resumed; a run that costs
  money asks first; an endpoint's cache is keyed by its URL too; core receives the clock.
- **Kept as limits** (design §18): the overall ceiling pools all held-out questions; the time estimate uses
  measured rates rather than a calibration call; an unreadable `llm` reranker reply keeps the retrieval
  order; the money estimate is an upper bound.
- **Status:** designer's choice.

## D-057: What the pre-release tests changed  (2026-11-22)

- **Found** by a security review, a new user's test of the built wheel against fakes, and real runs with
  local models on Chroma's chunking benchmark (its own 472 gold questions) and the FastAPI docs (159
  files, the default 540 questions). Confirmed by running each.
- **Choice:** the fixes listed in the change log under "Before release". Three are design choices:
  1. Among entries tied on dev, the order is now the cheaper, then the higher on dev, then the smaller,
     then the first listed (it was cheaper, smaller, first listed). A tie on dev is uncertainty, and the
     dev mean is still the best guess; a few tokens per question must not outweigh it.
  2. When the pipeline chosen on dev is separably behind the top on held-out, the board says so and
     suggests the top or more questions. The choice itself stays on dev, so held-out numbers stay honest.
  3. Passages are offered to the writer one document at a time (seeded), so coverage is spread across
     documents instead of following their length.
  4. A category stops after 60 drafts when fewer than 1 in 20 were kept, and says so: on the FastAPI
     docs, distractors kept 1 of 60 (the docs repeat themselves, so the look-alike passage also answers),
     and asking on would have taken an hour for a category that stays too few to rank.
  5. A user question may give `start`, its quote's character offset, so a quote found twice in one
     document is not dropped as ambiguous (67 of Chroma's 472 gold questions were).
  6. Under each board, a kind of question on which the chosen pipeline is separably behind another entry
     is named. On the FastAPI docs `bm25` was chosen (tied overall with `hybrid`) while scoring 0.02 on
     paraphrase questions against `hybrid`'s 0.18; the overall mean hid it.
  7. A model call the server refuses even after its retries (a 5xx, a timeout) costs one question, not
     the run: a question draft is dropped with the reason; an llm-reranker call is tried once more with
     sampling, then keeps the retrieval order and is counted under the board. Ollama answered 500
     ("token repeat limit reached") to one reranker call after 30 minutes of the FastAPI run.
  8. The time estimate uses the FastAPI run's measurements: 6 s per kept question, 2.7 s per reranker
     call (it estimated 125 minutes for a run that took about 71).
- **Kept as limits:** plain `http://` with a key is allowed (servers on a local network) and documented;
  the generated chunker's isolation is not a sandbox (approval is the safety step); on Windows a stale
  lock is not detected automatically (the message says which file to delete); Windows and macOS run in CI
  but were not tried by hand.
- **Status:** designer's choice.

## D-058: The design says only what is built: no `--no-cache`, no `hf:` tokenizers  (2026-11-24)

- **Found** by reading the design against the code: §10.2 named a `--no-cache` flag no command has, and
  §4.3 and §7.4 named `hf:<tokenizer id>` counting and the `tokenizers` package, which were never built
  (D-008 planned them).
- **Choice:** both promises are removed (owner, 2026-11-24). `ragcourt cache clear` covers the first.
  Loading a Hugging Face tokenizer by id downloads it from huggingface.co, which is against "nothing
  leaves the machine"; token counts stay `tiktoken:<encoding>` for the `endpoint` embedder, Ollama's own
  for local models, and labelled estimates otherwise. The unused `use_cache` switch of
  `Project.embedder` is deleted. Either could return through a change record.
- **Status:** owner's choice.

## D-059: The extra `pdf` is `pypdf`  (2026-11-24)

- **Measured** on 2026-11-24: `pypdf` 7.1.1 installs 1.9 MB with no dependency on Python 3.11 or newer
  (`uv pip install --target`), is BSD-3-Clause, and had six releases in the four weeks before. `pymupdf`
  extracts better but is AGPL; `pdfplumber` brings `pdfminer.six` and is slower.
- **Choice:** the optional extra `pdf = ["pypdf>=5"]` ([changes/0005](changes/0005-pdf.md)); the core still
  imports no extra. The owner chose no de-hyphenation: the text stays what the extractor gave. A PDF with a
  password is skipped even when `pypdf` could open it with an empty one. `.docx` stays out until it has
  its own record.
- **Status:** owner's choice (2026-11-24); the measurements are the designer's.

## D-060: Your own pipeline, as built  (2026-11-24)

- **Found** while building [changes/0006](changes/0006-your-own-pipeline.md). Four points differ from, or
  were left open by, the record:
  1. **A text found in more than one place is not scored.** The record said it would count as a hit "only
     if every place it could be holds the quote". That is never true for two different places, so the rule
     is said as what it does: its place is unknown, it scores nothing, and it is counted apart from texts
     that are not found. A corpus that holds the same document twice makes every chunk such a text.
  2. **One pipeline per run.** The run's blames, ceilings, `explain` and report are then plainly about
     that pipeline; two would need a second set of each.
  3. **On `--resume` the pipeline is asked again.** Its evaluation is saved like any other, but its chunk
     table lives only in the run, and blame needs it.
  4. **`pipeline_chunks` is its own decorator**, not an attribute of `pipeline` (no magic).
- **Also:** the steps of the greedy search moved from `flows/rank.py` to `flows/search_steps.py`, because
  the last step made `rank.py` pass the 250-line limit; nothing in them changed.
- **Status:** designer's choice.
