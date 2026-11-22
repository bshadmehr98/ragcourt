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
- Design 0001, accepted ([design/changes/0001-initial-design.md](design/changes/0001-initial-design.md)).
- Foundations (milestone 1, step 1): the typed errors; the `ragcourt.types` dataclasses and protocols;
  the stage registry with `@chunker`, `@embedder`, `@retriever` and `@reranker` and the user's
  `ragcourt_stages/` folder; `load_documents` for Markdown, text, reStructuredText and HTML;
  `load_config` for `ragcourt.toml`; `ragcourt.testing` with `FakeEmbedder`, `ScriptedModel` and a
  bundled corpus of thirteen documents.
