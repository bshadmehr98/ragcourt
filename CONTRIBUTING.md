# Contributing to ragdoctor

Thank you for helping. This page covers how to set up, the rules the code follows, how it is tested and
how the design changes. The design itself is in [`design/`](design/README.md); start with
[`design/current.md`](design/current.md). The first design, [0001](design/changes/0001-initial-design.md),
is proposed and waits for the owner.

## Setup and the quality gates

```bash
uv sync --all-extras          # install the package with every extra and the dev tools
scripts/check.sh              # every quality gate; "green" means this exits 0
```

The default test suite needs no model, no API key and no network.

`scripts/check.sh` runs ruff (lint and format), the import-layer check (`scripts/check_layers.py`),
pyright (strict for `src/`), the default test suite with branch coverage of at least 90% on `src/`,
`uv build`, and a smoke test that installs the built wheel alone in a fresh virtual environment (and runs
the README quickstart once there is one). Pull requests must keep it green. Never weaken a test to make
it pass.

Other useful commands:

```bash
uv run pytest                          # default suite: fast, offline, deterministic
uv run pytest tests/e2e                # the acceptance cases only
uv run ruff check . && uv run ruff format .
uv run pyright
uv run python scripts/check_layers.py  # the import layers alone
uv run pytest -m real_model            # real models (see below)
```

## Keep it simple

The first rule: **simple, easy to understand, maintainable and expandable.** When simplicity conflicts
with anything except correctness and the guarantees in [`design/current.md`](design/current.md#16-guarantees-acceptance-cases),
simplicity wins. A newcomer should be able to read the whole codebase in an evening and add a stage in one
file.

1. Build the simplest thing that passes the acceptance cases, not the most general thing.
2. No speculative generality. Add an abstraction only when there are two real uses today, or the design
   names it as an extension point (the four stage kinds and their registry, the model client's protocol).
3. Extend through the few seams named in the design: a stage is one file with a decorator. Everything
   else is ordinary concrete code.
4. Plain Python first: functions and small dataclasses before classes, composition before inheritance,
   the standard library before dependencies.
5. Flat and explicit: short call chains, no metaclasses, import hooks, monkey-patching or deep decorator
   stacks (the one registration decorator per stage is the only decorator the design asks for).
6. One obvious way to configure and call each thing.
7. Names over comments; comments say *why*.
8. Delete freely: dead code, unused parameters and single-caller helper layers go.

Limits, checked in review (ruff enforces complexity, `scripts/check_layers.py` the layers):

| Thing | Limit |
|---|---|
| Cyclomatic complexity per function | 10 (`C901`) |
| Function length | about 40 lines |
| Module length | about 300 lines |
| Parameters per function | 6; group more into a small dataclass |
| Inheritance depth of own classes | 1 |
| Variants | a dict of functions or a `match`, not a class hierarchy (stages are functions registered by name; audit checks are functions in a table) |
| Core dependencies | the standard library; anything else is an optional extra, and a new one needs a written reason in `design/decisions.md` |

Avoid "manager / handler / processor" layers, base classes with one subclass, plugin systems beyond the
stage registry, event buses and dependency-injection containers.

## Code conventions

- Python 3.11 or newer; ruff with line length 110; pyright strict for `src/`; the public API is fully
  typed and `py.typed` is shipped.
- The public API is exported from `src/ragdoctor/__init__.py` with an explicit `__all__`; public
  functions and classes have docstrings.
- **Layers import only downward** ([`design/current.md`](design/current.md) §3.1): `types` (dataclasses
  and protocols, no logic) → `stages` → `core` (pure functions) and `io` → `commands` (one file each) →
  `cli`. Stages never import each other; only the pipeline joins them. Each module's docstring names the
  design sections it implements.
- **The core is useful alone.** It never imports an optional extra at import time; stages that need one
  import it inside the function. `tests/unit/test_import_boundaries.py` checks this.
- **One client for every model.** Only the model client in `io` talks to the network, and only to an
  endpoint the user configured. Keys come from environment variables, never from a file ragdoctor writes.
  No telemetry. Document text never goes to logs.
- **Measured, or said to be unknown.** A token count from the embedder's own tokenizer is `measured`;
  anything else is labelled `estimated`. An unknown price is unknown, never zero.
- **Explicit failure.** Never swallow errors silently. Errors crossing the public API are typed
  (`RagDoctorError` and its subclasses in `errors.py`), and messages say what happened and what to do.
  Retryable endpoint failures (timeouts, 429, 5xx) are told apart from permanent ones.
- **Determinism.** Fixed seeds (the split, bootstrap resampling, sampling documents); explicit ordering
  and tie-breaking by stable ids; never `hash()` for anything stored.
- Paths are `pathlib.Path`; durations are integer milliseconds; logging goes to
  `logging.getLogger("ragdoctor")`; output for people is written by `commands` and `cli` only.

## Tests

| Suite | Folder | Runs by default | Purpose |
|---|---|---|---|
| Unit | `tests/unit/` | yes | each module's behaviour, edge cases and errors; metrics and blame against hand-worked numbers |
| Contract | `tests/contract/` | yes | every stage passes its kind's contract; the fake embedder and the scripted model behave like the client |
| Integration | `tests/integration/` | yes | modules together with real local resources: the filesystem, the cache file, a fake OpenAI-compatible server on a free port, a generated chunker in a subprocess |
| Acceptance | `tests/e2e/` | yes | the numbered guarantees of [`design/current.md`](design/current.md#16-guarantees-acceptance-cases), through the public API or the CLI only, on the bundled corpus |
| Real models | `tests/real/` | no | a local model server or an endpoint, marker `real_model`; by hand |

- The default suite must stay fast, deterministic and offline: the fake embedder and the scripted model
  from `ragdoctor.testing`, the bundled corpus in `tests/fixtures/corpus/`, fixed seeds.
- Every acceptance case has a test in `tests/e2e/` named `test_ac<N>_<slug>`, using only the public API or
  CLI. An acceptance test must fail if its feature is removed.
- Every metric, interval and blame rule has a test against numbers worked out by hand; every audit check
  has a case that triggers it and a near miss that must not.
- The README quickstart, every Python block in `docs/` and every file in `examples/` are run by the tests,
  once they exist. Each example opens with a What / How / Why docstring and is listed in
  `examples/README.md`.

### Real-model tests

The real-model tests (`-m real_model`, in `tests/real/`) run on the bundled corpus against a model chosen
by environment variables: `RAGDOCTOR_TEST_BASE_URL`, `RAGDOCTOR_TEST_API_KEY`,
`RAGDOCTOR_TEST_EMBED_MODEL`, `RAGDOCTOR_TEST_CHAT_MODEL` and `RAGDOCTOR_TEST_RERANK_MODEL`. A local
server (Ollama, llama.cpp, vLLM, LM Studio) is preferred; in-process local models need their extra. They
skip with a reason when something is missing. The `real-model-tests` skill in `.claude/skills/` says how
to run and write them, and how to keep what they show as fixtures for the default suite.

## Changing the design

Design changes are written down before they are built:

1. Write `design/changes/NNNN-<short-name>.md` with status `proposed` and the sections Status, Context,
   Problem, Options, Decision, Consequences, and Migration and compatibility.
2. The maintainer reviews it; the status becomes `accepted` (or `rejected`).
3. Implement it from [`design/current.md`](design/current.md) and the accepted change records, tests
   first.
4. Update `design/current.md`, set the record to `implemented in <version>`, and add a `CHANGELOG.md`
   entry that links to it.

Smaller implementation choices that need no change record go into
[`design/decisions.md`](design/decisions.md).

## Branches and pull requests

- One branch per change, named `<type>/<short-name>` after the Conventional Commit types
  (`feat/budget-recall`).
- While the repository is local only, the maintainer merges finished branches into `main`.
- Once published: fill in [`.github/pull_request_template.md`](.github/pull_request_template.md); claude[bot]
  reviews every pull request ([`.github/workflows/claude-review.yml`](.github/workflows/claude-review.yml));
  answer each thread; `main` accepts changes only through pull requests with CI green and every review
  thread resolved; the maintainer merges.

## Commits

- Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`, `build:`, `ci:`), a
  subject of at most 72 characters, a body that explains why; one logical change per commit.
- Commits written with an AI tool end with a `Co-Authored-By:` line naming it.
- Never commit API keys, a user's documents, generated question sets from private documents, or results.
- `CHANGELOG.md` follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

Contributors using AI coding tools will find a short brief for them in [`AGENTS.md`](AGENTS.md); Claude
Code users also get the whole workflow as skills, reviewer agents and hooks in [`.claude/`](.claude/).
