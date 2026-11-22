# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow semantic versioning. Why the
design changed is in [`design/changes/`](design/changes/).

## [Unreleased]

### Added

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
