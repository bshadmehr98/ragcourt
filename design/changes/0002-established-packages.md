# 0002: Use established packages instead of hand-written ones

## Status

`proposed` (2026-11-23). Replaces D-003 ("the core is the standard library alone"), which was a
designer's choice, not the owner's.

## Context

On 2026-11-23 the owner set the rule for dependencies:

> We want this package to be as small as possible, but without losing any functionality. We don't want to
> reinvent the wheel. And we don't want to make it complicated for a first user to understand.

and defined what to avoid: packages with a small community, and building ragcourt on top of other RAG
packages. A package that everyone uses (as everyone used `requests`) should be used.

D-003 went further: no dependency at all. It kept the install small, but it made ragcourt write its own
file lock, HTTP client, TOML editing and memory check. One of these caused a real bug: `urllib` sends
every header, the API key included, to wherever a redirect points (fixed in D-057 by refusing redirects).

## Problem

Which hand-written parts should become a package, by the owner's three tests:

1. **Smaller:** the package removes our code or our risk, and its own install is light.
2. **No lost function:** every guarantee of design §16 and every current test still holds.
3. **No harder to understand:** the install command, the settings and the output stay the same for a
   first user; a contributor reads a library they likely know instead of our version of it.

## The rule (replaces D-003)

A core dependency is allowed when **all** of these hold:

- **Widely used and maintained:** among the packages most Python projects already meet; releases within
  the last year; more than one maintainer or an organisation behind it.
- **A general job:** HTTP, file locks, TOML, system information, arrays. Never a RAG framework (LangChain,
  LlamaIndex, chonkie, Ragas): ragcourt judges those, so it is not built on them. They stay optional
  extras, as now.
- **It earns its place:** it removes our code or a risk we would otherwise carry. A package that only
  changes how something looks, or that adds code around it, is not added.
- **It fits beside the user's project:** a lower bound only (`httpx>=0.27`), never a pin; heavy packages
  (torch, sentence-transformers) stay optional extras.

Each core dependency gets a line in `design/decisions.md` with its reason, and a test lists the core
dependencies so a new one cannot arrive unnoticed.

## Options

1. **Leave it as it is:** the standard library alone. Smallest install, but we keep maintaining our own
   lock (which cannot tell a crashed run from a live one on Windows), our own HTTP code and our own TOML
   editing, and setup reads 0 GB of RAM on Windows.
2. **Swap every generic part for a package** (HTTP SDKs, rich, jinja2, BeautifulSoup, click): less of our
   code in some places, but heavier installs, and several swaps fail the tests above (below).
3. **Swap only where a package passes all three tests** (chosen).

## Decision

Option 3. Each candidate was checked against the code it would replace; installed sizes were measured with
`uv pip install --target` on Python 3.12.

### Adopt

| Package | Size | Replaces | Gain |
|---|---|---|---|
| `filelock` | 1.3 MB | `io/lock.py` (66 lines: process ids, a liveness check, a Windows guess) | The operating system releases the lock when a process dies, so a crashed run never blocks the next one, on any OS. Today on Windows it blocks until the user deletes the file. About 40 lines fewer. |
| `tomlkit` | 0.25 MB | `io/toml_edit.py` (46 lines of line-matching regexes) | `models set` edits `ragcourt.toml` with a real TOML parser that keeps comments; no hand-written escaping (`json.dumps` is not TOML escaping for every character). About 25 lines fewer. Reading stays on the standard library's `tomllib`. |
| `psutil` | 0.5 MB | the RAM half of `io/machine.py` | Total memory on Windows, where `os.sysconf` does not exist and `setup` now reads 0 GB and recommends the smallest model. The GPU part stays on `nvidia-smi` (psutil does not report GPUs). |
| `requests` | 2.2 MB | the transport in `io/http.py` (111 lines) | Redirects are refused with one argument (`allow_redirects=False`) instead of our `urllib` subclass, and requests drops the key on a redirect to another host even if one were followed; plain timeouts and errors; connections reused. Our retry rules, reply limit and messages stay. About 20 lines fewer, and the one `urllib` subclass allowed by `check_simple.py` goes away. The smallest gain of the four: see open question 2. |

`httpx` was the first candidate; it fails the rule: its last release was 0.28.1 on 2024-12-06, and its
best-known user, the openai SDK, has moved to a fork (`httpx2`). requests had a release on 2026-05-14.

### Open question: `numpy` for vector math

| Package | Size | Replaces | Gain |
|---|---|---|---|
| `numpy` | 53 MB | the pure-Python cosine in `stages/retrievers/dense.py` and the `array` reading in `io/cache.py` | Measured: 98 ms per question over 5,000 chunks of 768 dimensions in pure Python, 4.8 ms with numpy (20 times faster). A 400-question run scores each question once per pipeline and again in probes, so on a corpus that size pure Python spends minutes on arithmetic. |

It adds no function and no fewer lines; it is speed for size. Most users already have it: chonkie (our own
extra), Chroma, FAISS, sentence-transformers and LlamaIndex all require numpy, so the added size is usually
zero. The design's claim that plain Python is "fine to about 200k chunks" (§18, tutorial chapter 6) does
not hold by this measurement: 200k chunks would take about 4 seconds per question and several GB of memory
as Python lists. With numpy, the claim is corrected from a new measurement; without it, it is lowered to
what the measurement supports.

### Measured and rejected

- **BeautifulSoup + markdownify for HTML** (`io/html_text.py`, 179 lines): prototyped against the 28 cases
  in `tests/unit/test_html_text.py`. With Python's parser 13 of 28 matched: a `<head>` left open lost the
  whole page, and tables with omitted `</td>` broke apart. With `lxml` (a third package) and tuned options,
  19 of 28: nested tables, a `<pre>` in a cell, captions and empty tables still came out wrong, and line
  breaks in a paragraph were kept, which changes the text gold quotes are found in. Matching our behaviour
  would need a custom converter subclass, so the code would not shrink. **Keep ours.**
- **rich for the terminal** (7 MB): the tables are 30 lines. rich wraps tables to the terminal's width
  (80 columns in a pipe), which breaks long pipeline names in logs and in the tests that compare text, and
  it reads `[bold]` in model text as markup, so every model text would need escaping on top of the
  existing hidden-character escaping. More code, not less. **Keep ours.**
- **The openai and ollama SDKs:** they bring pydantic, anyio and their own retries and redirect rules;
  `/rerank` is in neither, so our HTTP code would stay anyway.
- **jinja2 for the report:** the report would move into a template file of about the same length.
- **click or typer instead of argparse:** argparse is the standard library, not a wheel we reinvented.
- **rank-bm25 or bm25s:** rank-bm25 has had no release since 2022. bm25s is maintained, but has its own
  tokenizer and stemming; to count the same words as the rest of ragcourt we would pass it ours, and what
  is left of our 55 lines is the formula itself.
- **scipy for intervals:** about 40 MB, and the mean-of-category-means bootstrap is not its stock bootstrap.
- **nltk, pysbd, markdown-it-py for sentences and structure:** nltk needs a data download; pysbd has had
  no release since 2021; markdown-it-py reads Markdown only and would lose the reStructuredText headings that
  `core/structure.py` finds.

### What a user sees

Nothing new to learn: the same `pip install ragcourt` (or `uv tool install ragcourt`), the same settings,
the same output. Two messages change for the better: a run never says "delete the lock file" again, and
`setup` on Windows names the machine's RAM.

## Consequences

- Core dependencies: `filelock`, `tomlkit`, `psutil`, `requests`, and `numpy` if the owner agrees.
  Install grows by about 4.3 MB without numpy (often 0 MB more with it, since most environments have it).
- About 90 lines of our code go (lock, TOML editing, HTTP transport, Windows memory); the `urllib`
  redirect-handler exception in `scripts/check_simple.py` goes.
- The rules that said "standard library" change to this record's rule: AGENTS.md rule 1,
  CONTRIBUTING.md ("What we build with" and its table), the `plan-change` and `keep-it-simple` skills, the
  `simplicity-reviewer` agent, the comment in `pyproject.toml`, design/current.md §3 and §11.1.
- `core` stays pure: these packages are used only in `io` and, for numpy, in the dense retriever and the
  cache; `scripts/check_layers.py` is unchanged.

## Risks answered

- **Numbers are measured / blame is code / gold independent of chunking:** untouched; no metric, rule or
  question changes. With numpy, scores are computed in float32 as the cache already stores them; ties stay
  broken by chunk index.
- **Privacy:** requests contacts only the configured addresses, with redirects off; it sends no
  telemetry.
- **Files:** no file format changes; the cache stays `vectors.f32`; the lock file keeps its name.
- **Nothing happens blindly, generated code:** untouched.
- **Simplicity:** no new kind of configuration, class hierarchy, thread or database; three modules get
  shorter.

## Acceptance cases (design §16)

34. **Core dependencies are listed.** The core dependencies in `pyproject.toml` are exactly those with an
    entry in `design/decisions.md`, each with a lower bound only; a test fails on any other.
35. **A crashed run never blocks the next.** A process holding the working folder's lock that is killed
    leaves no lock behind: the next command runs, on Linux, macOS and Windows (the CI matrix).

## Tests

- Every existing test passes unchanged in what it checks, notably `tests/integration/test_hostile_servers.py`
  (redirects refused, reply limit, retries on 429 and 5xx, malformed replies) and `tests/unit/test_lock.py`.
- New: AC34 (dependency list), AC35 (a killed holder), `models set` on a file with comments, strings that
  need TOML escaping and a missing `[models]` section; `ram_gb` returns more than 0 on every CI system.
- With numpy: `dense` returns the same order as today on the bundled corpus, ties by index.
- The wheel smoke test installs the dependencies from a clean environment; the real-model tests run once.

## Migration and compatibility

Unreleased, so no user is affected. A lock file left by an older build is replaced on the next run. No
file formats change, so question sets, caches and results stay valid.

## Open questions for the owner

1. **numpy:** 53 MB for 20 times faster scoring on large corpora (recommended: yes, since most RAG setups
   already have it).
2. **requests:** about 20 lines fewer and safer defaults for 2.2 MB (recommended: yes, as the clearest
   case of a wheel we reinvented); or keep `urllib`, which now works and is tested against hostile
   servers.
3. Anything on the rejected list you want reconsidered.
