# AGENTS.md: ragcourt

A brief for AI coding tools (Claude Code, Codex, Cursor and others) helping with this repository.
People follow the same rules; they are in [CONTRIBUTING.md](CONTRIBUTING.md).

## What this is

ragcourt (package, import and command `ragcourt`) is an open-source command-line tool
for RAG developers: it ranks chunkers, embedding models, retrievers and rerankers on the user's own
documents, and says which stage caused each miss. It runs on local models through Ollama by default:
`setup` picks and pulls models that fit the machine; `rank` measures pipelines against questions whose
gold answers are exact quotes from the source, filtered by a judge model that must first pass a
self-test; `audit` checks chunks by code; `explain` names the stage that lost each failed question and
what would fix it; `doctor` lets a model propose (and write) a chunker, which is shown, approved,
isolated, validated and measured like any other. Read
[design/current.md](design/current.md) before changing behaviour; its §16 lists the guarantees the tests
check and its §17 says what is built. Why the design looks like this: the owner's brief in
[design/history/0001-owner-brief.md](design/history/0001-owner-brief.md),
[design/changes/](design/changes/) and [design/decisions.md](design/decisions.md).

**Status:** design 0001 is proposed and waits for the owner's acceptance. Nothing of the product is
built: the package holds its version and its base error. Do not implement anything the design does not
say; a gap becomes a `D-` entry or a proposed change record.

## Commands

```bash
uv sync --all-extras                 # install everything (dev included)
scripts/check.sh                     # all quality gates: lint, format, import layers, simplicity, types, tests + coverage, build, wheel smoke test
uv run pytest                        # default suite (fast, offline, deterministic; fake embedder, scripted model)
uv run pytest -m real_model          # real models: a local server or an endpoint; by hand (real-model-tests)
uv run python scripts/check_layers.py   # the import layers of design §3.1 alone
```

## Layout

The layers of design §3.1; each module's docstring names the sections it implements. Planned, built
milestone by milestone:

```
src/ragcourt/
  __init__.py  errors.py       the public API with an explicit __all__; RagCourtError and its subclasses
  types.py                     dataclasses and protocols, no logic (layer 0)
  stages/                      the registry and its decorators (__init__); chunkers/, embedders/, retrievers/, rerankers/: one file per stage (layer 1)
  core/                        pure functions: offsets, pipeline, metrics, stats, blame, search, audit (layer 2)
  io/                          loaders, the model client, the cache, questions, the report, config (layer 2)
  commands/                    setup, audit, rank, explain, doctor: one file each (layer 3)
  cli.py                       the command line (layer 4)
  testing/                     the fake embedder, the scripted model, the bundled corpus
tests/unit|contract|integration|e2e   default suite; tests/real: by hand, marked real_model
scripts/check.sh                     the one gate
scripts/check_layers.py  check_simple.py   the import layers; the simplicity rules ruff can't check
design/                why and how: README, current.md, changes/, decisions.md, history/
docs/  examples/       user docs and runnable examples, both executed by tests once they exist
```

## Rules

1. **Simple first** ([CONTRIBUTING.md](CONTRIBUTING.md#keep-it-simple), the `keep-it-simple` skill): the
   plainest code that meets the guarantees. The standard library, plain files (no database), sequential
   code, functions and frozen dataclasses, no magic. Small modules of one concept (≤ 250 lines, aim
   150), short flat functions (≤ 40 lines, ≤ 3 nested blocks), comprehensions with one `for` and at most
   one `if`. Every extension is one new file. `scripts/check_simple.py` and ruff check it.
2. **Layers import only downward** (design §3.1): types → stages → core and io → commands → cli. Stages
   never import each other; only the pipeline joins them. `scripts/check_layers.py` enforces it.
3. **Numbers are measured:** every number in a ranking is computed on the user's documents, on the
   held-out split, with its uncertainty; ties are reported as "no significant difference"; nothing (not
   even a chunker doctor wrote) is called better without the measurement. Unknown is said, never filled
   in (an estimated token count is labelled estimated; an unknown price is unknown).
4. **Blame is code:** each miss gets exactly one cause, a stage and a mechanism, from offsets, ranks,
   scores and probes (design §9), with its evidence and whether a measurement confirms it; a model is
   never asked who is to blame. A judge only filters questions (and, as a reranker, orders candidates),
   and only after passing its self-test (design §6.6).
5. **Gold is independent of chunking:** a question's gold answer is an exact quote found verbatim in the
   source; no question depends on a chunker; a quote that is not found drops its question.
6. **Nothing leaves the machine** unless the user configured that endpoint (Ollama on `localhost` is the
   default); one client for every model; no model is downloaded without the user's yes;
   keys only from the environment; no telemetry; document text never goes to logs.
7. **Nothing happens blindly** (design D-030): before a model is called, the user sees the plan (each
   role, its model, where that choice came from, what the model is shown); before the first judge call,
   what the judge is asked and shown and what it never decides; prompts and the judge's test cases are
   readable files; every verdict keeps its reason; outputs carry a legend of their rules. Code a model
   wrote is shown, runs only after the user approves it, only in a subprocess with a timeout, and its
   output is validated before it is used.
8. **Design before code:** a new need or change starts as `design/changes/NNNN-<name>.md` with status
   `proposed`; the maintainer accepts it before it is built. Small choices go into `design/decisions.md`.
9. **The default suite is offline and deterministic:** the fake embedder, the scripted model, the bundled
   corpus, fixed seeds; real models only in `tests/real/` (marker `real_model`). Never commit a user's
   documents, keys or results.
10. **Git**: Conventional Commits, small commits; AI-written commits end with a `Co-Authored-By:` line.
    The repository is local only for now: never push, tag or publish unless the maintainer asks.
