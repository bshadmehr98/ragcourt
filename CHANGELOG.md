# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow semantic versioning. Why the
design changed is in [`design/changes/`](design/changes/).

## [Unreleased]

### Added

- `ragcourt demo`: in under a minute, with no model and no network, a live audit of the bundled documents
  and a real run on them recorded with local models, labelled as recorded; the README now opens with its
  output ([design/changes/0003-demo-and-readme.md](design/changes/0003-demo-and-readme.md)).
- `ragcourt rank --pipeline NAME`: a retrieval system of your own, wrapped in one `@pipeline` function, is
  scored on the same questions and its misses are blamed; `--no-search` runs only yours
  ([design/changes/0006-your-own-pipeline.md](design/changes/0006-your-own-pipeline.md)).
- PDF documents with the optional extra `pdf` (`pip install 'ragcourt[pdf]'`); a PDF that cannot be read
  is skipped with its reason ([design/changes/0005-pdf.md](design/changes/0005-pdf.md)).
- `ragcourt rank --quick`: a quick look with 20 questions per category that shows where the misses are
  and never names a winner; the full run reuses its questions
  ([design/changes/0004-quick-look.md](design/changes/0004-quick-look.md)).
- The repository in the shape of the owner's other projects: the contributor rules, the Claude Code
  workflow (skills, hooks, reviewer agents), the GitHub workflows, `scripts/check.sh` with the
  import-layer check, and the package skeleton with its base error.
- The simplicity rules of CONTRIBUTING.md, checked by `scripts/check_simple.py` in the gate.
- Design 0001, accepted and implemented ([design/changes/0001-initial-design.md](design/changes/0001-initial-design.md)).
- Foundations (milestone 1, step 1): the typed errors; the `ragcourt.types` dataclasses and protocols;
  the stage registry with `@chunker`, `@embedder`, `@retriever` and `@reranker` and the user's
  `ragcourt_stages/` folder; `load_documents` for Markdown, text, reStructuredText and HTML;
  `load_config` for `ragcourt.toml`; `ragcourt.testing` with `FakeEmbedder`, `ScriptedModel` and a
  bundled corpus of thirteen documents.
- The audit (milestone 1, step 2): offsets found by code, the four native chunkers, the eight checks,
  `ragcourt audit` with measured or estimated sizes, `--show`, `--json` and `--fail-on`.
- Local models (step 3): one client for Ollama and OpenAI-compatible endpoints, the `ollama` and
  `endpoint` embedders with measured limits and documented prefixes, the plain-file embedding cache,
  `ragcourt setup`, `models` and `prompts`, every section of `ragcourt.toml`.
- Questions and the judge (step 4): six categories, the writer and judge prompts as files, code rules,
  the judge's checks with a reason on every verdict, its self-test, user questions, splits, `ragcourt
  questions` and `questions show`.
- Ranking (steps 5 and 6): dense, BM25 and hybrid retrievers; none, llm, endpoint and cross-encoder
  rerankers; chonkie, LangChain and sentence-transformers adapters; every metric with intervals, ties and
  the smallest difference; the greedy search; blame by stage and mechanism with probes, fixes, levels and
  ceilings; the plan, estimate and budgets; progress and resume; `ragcourt rank` and `explain`.
- The HTML report (step 7) and `ragcourt report`; doctor (step 8) with approval by hash and an isolated run.
- Documentation and twelve offline examples (step 9), and `tutorial/`: RAG retrieval and ragcourt from
  zero in 21 chapters, including the real runs, with a quick tour in the README.
- HTML pages keep only their marked main content and drop navigation (D-040).
- Embedders return token counts with their vectors and know questions from chunks (D-041, D-042).

### Fixed

- HTML that leaves out `</tr>`, `</td>` or `</head>` no longer loses tables or the whole body; nested
  tables and code in cells stay in their row; blank lines in `<pre>` are kept.
- An unreadable document, or a `ragcourt.toml` that is not UTF-8, is reported instead of crashing; a
  byte-order mark no longer hides a file's first heading.
- The stage registry refuses one name defined twice in one file, names that would break a stage spec,
  and non-functions; unknown kinds are a `ConfigError`; hidden files in `ragcourt_stages/` are not run,
  and a stage file can import a helper beside it.
- Before release (D-057), from a security review, a new user's test of the built wheel and real runs on
  Chroma's chunking benchmark and the FastAPI docs:
  - **Security:** a key is never sent to an address a server redirects to; corpus links that point
    outside the folder are skipped; control and bidirectional characters from documents or models are
    escaped on the terminal, and model-written code holding them is refused; approved code is re-hashed
    before every run, its output files capped and its process group stopped on a timeout; replies are
    size-capped and malformed ones are one-line errors; report filters use no inline JavaScript; HTML over
    5 MB is skipped; GitHub Actions are pinned to commits and the review workflow takes its instructions
    from `main`.
  - **Never a traceback:** a wrong run id, an unreadable questions file, a folder that cannot be written,
    unknown metrics, categories, retrievers or rerankers, out-of-range settings and chunker sizes are one
    message, before the plan; missing Ollama models are named before any question is written; `models
    set` never writes a model that is not installed; one ragcourt at a time per working folder.
  - **Results:** among entries tied on dev, the higher dev score now beats a few tokens less (the Chroma
    run kept `dense` over a separably better `hybrid`), and a choice behind on held-out is pointed out;
    the doctor's verdict uses the categories its board ranks; questions are drawn from every document in
    turn, so one long changelog no longer supplies most of them; a quote with Markdown links is prose.
  - **Speed and use:** chunking and the near-duplicate check are linear in a document's length (4 MB: 80
    s, now 9 s); runs on your own questions alone (`--questions 0`) call no writer or judge, and the plan
    counts them; output is line-buffered; `--json` is offered where it works; audit lists skipped files.
