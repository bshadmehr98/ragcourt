# Contributing to ragcourt

Thank you for helping. This page covers how to set up, the rules the code follows, how it is tested and
how the design changes. The design itself is in [`design/`](design/README.md); start with
[`design/current.md`](design/current.md). The first design, [0001](design/changes/0001-initial-design.md),
is implemented (0.1, unreleased).

## Setup and the quality gates

```bash
uv sync --all-extras --no-extra local   # the package, the light extras and the dev tools (`--extra local` brings torch)
scripts/check.sh              # every quality gate; "green" means this exits 0
```

The default test suite needs no model, no API key and no network.

`scripts/check.sh` runs ruff (lint and format), the import-layer check (`scripts/check_layers.py`), the
simplicity check (`scripts/check_simple.py`),
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
uv run python scripts/check_simple.py  # the simplicity rules ruff can't check
uv run pytest -m real_model            # real models (see below)
```

## Keep it simple

The first rule: **simple, easy to understand, maintainable and easy to extend.** When simplicity
conflicts with anything except correctness and the guarantees in
[`design/current.md`](design/current.md#16-guarantees-acceptance-cases), simplicity wins. A newcomer
should read the whole codebase in an evening, understand any module in a few minutes, change it safely
and add a stage in one file. The `keep-it-simple` skill in `.claude/skills/` is the same list as a working
checklist.

### What we build with

1. **The standard library.** No core dependency; an optional extra only with a written reason in
   `design/decisions.md`.
2. **Plain files, no database.** Text the user can open: JSON, JSONL, TOML, Markdown. The embedding cache
   is a folder of files (design §10.2). No SQLite, no ORM, no server, no daemon, no background process
   other than doctor's one subprocess.
3. **Sequential code.** No `async`, no threads, no process pools. If a measurement ever shows the need,
   it goes in one module behind a design decision.
4. **Functions and dataclasses.** Data is a `@dataclass(frozen=True)` (or a plain dict read from a
   file); behaviour is a function. A class with methods only where state truly belongs to it (the model
   client holding its connection settings). The only inheritance: `typing.Protocol`, enums, the errors
   in `errors.py`, and `html.parser.HTMLParser`, which the standard library offers only as a base class.
5. **No magic.** No metaclasses, `__getattr__` tricks, monkey-patching, `eval`/`exec`, `global`, import
   hooks or code generation. The one dynamic import is the stage loader (design §7.2). The one decorator
   the design asks for is a stage's registration.

### How code is shaped

6. **Small modules, one concept each.** A module holds one idea a reader can name in a few words, and its
   docstring says which design sections it implements. Aim for under 150 lines; 250 is the limit. When a
   module grows, split it by concept, not by size (one file per stage, per audit check, per question
   category, per stage of blame).
7. **Short, flat functions.** Aim for under 25 lines; 40 is the limit. At most three levels of nested
   blocks; return early instead of nesting. At most six parameters; group more into a dataclass.
   Boolean options are keyword-only (`*, dry_run: bool`).
8. **Readable expressions.** A comprehension has one `for` and at most one `if`; anything more is a loop.
   No nested conditional expressions, no walrus, no chained clever one-liners: name the intermediate
   value. A lambda only as a short sort key.
9. **Explicit over implicit.** Pass values in and return them; no module-level mutable state except the
   stage registry; no hidden I/O in `core` (it is pure, design §3.1). One way to configure each thing:
   `ragcourt.toml`, then flags.
10. **Names that say what.** Full words (`chunk_spans`, not `cs`); the words of design §2; no module named
    `utils`, `helpers`, `common`, `misc`, `manager` or `base`. Comments say *why*, never *what*; no
    commented-out code.
11. **No speculative generality.** Add an abstraction when there are two real uses today or the design
    names an extension point. Delete freely: dead code, unused parameters, single-caller helper layers.

### How it grows

Every extension point is "add one file and, where order matters, one line in a list". Nothing else
changes:

| To add | Touch | Design |
|---|---|---|
| a chunker, embedder, retriever or reranker | one file in `src/ragcourt/stages/<kind>/` with its decorator (or in the user's `ragcourt_stages/`) | §7 |
| an audit check | one file in `src/ragcourt/core/audit/` and its line in the list of checks | §5.1 |
| a question category | one file in `src/ragcourt/core/categories/`, its prompt in `src/ragcourt/prompts/`, its line in the list | §6.7 |
| a blame mechanism | one function in the file of its stage in `src/ragcourt/core/blame/`, its place in that stage's ordered list | §9.1 |
| a metric | one function in `src/ragcourt/core/metrics.py` and its line in the metrics table | §8.3 |
| a command | one file in `src/ragcourt/commands/` and its line in `cli.py` | §13.1 |
| a prompt change | the text file in `src/ragcourt/prompts/` and its version | §6.6 |

### Limits

Checked by ruff and `scripts/check_simple.py` in `scripts/check.sh`; never silenced with `noqa`
without a comment that says why, and never "fixed" by splitting code into pieces that mean nothing.

| Thing | Limit |
|---|---|
| Module length | 250 lines (aim for under 150) |
| Function length | 40 lines without the docstring (aim for under 25) |
| Nested blocks in a function | 3 |
| Cyclomatic complexity per function | 10 (`C901`) |
| Branches, returns, statements per function | 10, 5, 30 |
| Parameters per function | 6; boolean ones keyword-only |
| Comprehension | one `for`, at most one `if`, none inside another |
| Inheritance | `Protocol`, enums, the errors and `HTMLParser` only |
| Imports | downward only (design §3.1, `scripts/check_layers.py`) |
| Core dependencies | the standard library |

Avoid "manager / handler / processor" layers, base classes, plugin systems beyond the stage registry,
event buses, dependency-injection containers, caches beyond the embedding cache, and configuration
beyond one TOML file and flags.

## Code conventions

- Python 3.11 or newer; ruff with line length 110; pyright strict for `src/`; the public API is fully
  typed and `py.typed` is shipped.
- The public API is exported from `src/ragcourt/__init__.py` with an explicit `__all__`; public
  functions and classes have docstrings.
- **Layers import only downward** ([`design/current.md`](design/current.md) §3.1): `types` (dataclasses
  and protocols, no logic) → `stages` → `core` (pure functions) and `io` → `commands` (one file each) →
  `cli`. Stages never import each other; only the pipeline joins them. Each module's docstring names the
  design sections it implements.
- **The core is useful alone.** It never imports an optional extra at import time; stages that need one
  import it inside the function. `tests/unit/test_import_boundaries.py` checks this.
- **One client for every model.** Only the model client in `io` talks to the network, and only to an
  endpoint the user configured. Keys come from environment variables, never from a file ragcourt writes.
  No telemetry. Document text never goes to logs.
- **Measured, or said to be unknown.** A token count from the embedder's own tokenizer is `measured`;
  anything else is labelled `estimated`. An unknown price is unknown, never zero.
- **Explicit failure.** Never swallow errors silently. Errors crossing the public API are typed
  (`RagCourtError` and its subclasses in `errors.py`), and messages say what happened and what to do.
  Retryable endpoint failures (timeouts, 429, 5xx) are told apart from permanent ones.
- **Determinism.** Fixed seeds (the split, bootstrap resampling, sampling documents); explicit ordering
  and tie-breaking by stable ids; never `hash()` for anything stored.
- Paths are `pathlib.Path`; durations are integer milliseconds; logging goes to
  `logging.getLogger("ragcourt")`; output for people is written by `commands` and `cli` only.

## Tests

| Suite | Folder | Runs by default | Purpose |
|---|---|---|---|
| Unit | `tests/unit/` | yes | each module's behaviour, edge cases and errors; metrics and blame against hand-worked numbers |
| Contract | `tests/contract/` | yes | every stage passes its kind's contract; the fake embedder and the scripted model behave like the client |
| Integration | `tests/integration/` | yes | modules together with real local resources: the filesystem, the cache file, a fake OpenAI-compatible server on a free port, a generated chunker in a subprocess |
| Acceptance | `tests/e2e/` | yes | the numbered guarantees of [`design/current.md`](design/current.md#16-guarantees-acceptance-cases), through the public API or the CLI only, on the bundled corpus |
| Real models | `tests/real/` | no | a local model server or an endpoint, marker `real_model`; by hand |

- The default suite must stay fast, deterministic and offline: the fake embedder and the scripted model
  from `ragcourt.testing`, the bundled corpus (`src/ragcourt/testing/corpus/`), fixed seeds.
- Every acceptance case has a test in `tests/e2e/` named `test_ac<N>_<slug>`, using only the public API or
  CLI. An acceptance test must fail if its feature is removed.
- Every metric, interval and blame rule has a test against numbers worked out by hand; every audit check
  has a case that triggers it and a near miss that must not.
- The README quickstart, every Python block in `docs/` and every file in `examples/` are run by the tests,
  once they exist. Each example opens with a What / How / Why docstring and is listed in
  `examples/README.md`.

### Real-model tests

The real-model tests (`-m real_model`, in `tests/real/`) run on the bundled corpus against a model chosen
by environment variables: `RAGCOURT_TEST_BASE_URL`, `RAGCOURT_TEST_API_KEY`,
`RAGCOURT_TEST_EMBED_MODEL`, `RAGCOURT_TEST_CHAT_MODEL` and `RAGCOURT_TEST_RERANK_MODEL`. A local
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
