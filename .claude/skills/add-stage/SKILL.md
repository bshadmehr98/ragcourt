---
name: add-stage
description: Add a stage to ragdoctor - a chunker, embedder, retriever or reranker - in one file, registered with its decorator, with its tests, docs and (for a library adapter) its optional extra. Use when adding a native stage, a thin adapter for an existing library, or a new kind of model endpoint behind the one client.
---

# Add a stage

A stage is one implementation of one of the four kinds of `design/current.md` §7.1: a chunker, an
embedder, a retriever or a reranker. Adding one to the built-ins is a small change when it fits the kind's
signature; a new kind, a change to a signature, or a new extra is a design change: `plan-change` first.

1. **One file.** `src/ragdoctor/stages/<kind>/<name>.py`, registered with the kind's decorator from
   `ragdoctor.stages` (§7.2). The name is stable: results files and the user's configuration refer to it,
   and a removed name stays reserved (`deprecate-and-migrate`).
2. **Imports go down only** (§3.1): a stage imports `ragdoctor.types`, `ragdoctor.errors` and the
   registry, never another stage, `core`, `io` or a command. `scripts/check_layers.py` fails otherwise. A
   stage that needs a model receives the client through the protocol in `ragdoctor.types` (§11.1); it
   never opens a connection itself.
3. **The kind's contract.** A chunker is a function from text to a list of strings; it never computes
   offsets (the pipeline finds them, §4.2) and every string it returns must be found in the text. An
   embedder states its model id, its input limit and how its tokens are counted (§4.3); it never caches
   (the cache wraps it, §10.2). Retrievers and rerankers return scores, never a cut-off.
4. **A library adapter is thin.** It turns the library's output into the kind's signature and nothing
   more. Add the extra in `pyproject.toml`, import the library only inside the function, so the core
   imports without it (`tests/unit/test_import_boundaries.py`), and give a clear `RagDoctorError` naming
   the extra to install when it is missing.
5. **Deterministic.** Same input, same output; no randomness without a fixed seed; no network in the
   default suite.
6. **Tests.** A unit test of the stage on the bundled corpus (`tests/fixtures/corpus/`) with the fake
   embedder and the scripted model, including its edge cases (empty text, one long line, Unicode); the
   kind's contract test in `tests/contract/`; for an adapter or a model-backed stage, a marked test with
   the real library or model (`real-model-tests`).
7. `sync-docs`: `docs/stages.md` (the table of built-in stages and what each needs), the extras in
   `README.md`, an example if it shows a new idea.
