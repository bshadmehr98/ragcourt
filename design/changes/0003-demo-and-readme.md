# 0003: A one-minute demo, and a README that shows output

## Status

`implemented in 0.1` (accepted by the maintainer 2026-11-24, proposed the same day; what building it changed is D-061). The owner's answers: the README shows text, no image; `demo` prints the report's path and opens nothing.

## Context

On 2026-11-24 the owner set two goals for the repository, teaching and being a tool people use and star,
with the weight on the second. A visitor decides in about a minute. Today that minute shows a README
without one line of output, and the first real result needs Ollama, a 6.6 GB model and a run of an hour
(design §18). The brief's "useful result in under a minute" was dropped for good reason (D-034): a
trustworthy ranking needs hundreds of questions. Nothing replaced it.

## Problem

Show a new user what ragcourt finds, truthfully, in under a minute, with no model, no key and no network,
and without a ranking on too few questions.

## Options

1. **Leave it as it is.** The tutorial's chapter 19 holds real output, 19 chapters deep.
2. **Run live against the fakes** (`offline_project`): everything is computed, but by a fake embedder and
   a scripted model. The numbers mean nothing, and showing them as a result breaks "numbers are measured".
3. **Replay a recorded real run** on the bundled corpus (chosen): the audit is computed live (it needs no
   model); the ranking, the blame and the report come from a `results.json` recorded once with real local
   models and shipped in the package, labelled as recorded.

## Decision

Option 3: a new command, and a new README top.

```text
$ ragcourt demo
1. Audit, computed now on the 13 bundled documents (sizes estimated: no model is contacted)
   … the audit table of two chunkers …
2. A ranking recorded on 2026-11-2x with gemma4 and nomic-embed-text on an RTX 4060 (8 GB), 1xx questions
   … the four boards, with intervals and ties, as `rank` printed them …
3. Three of its misses, explained
   … as `explain` prints them …
4. The same as one page: .ragcourt/demo/report.html
Now your documents: `ragcourt setup`, then `ragcourt rank DOCS`.
```

- `ragcourt demo` contacts nothing, not even the local Ollama, and writes one file,
  `.ragcourt/demo/report.html`.
- The recording is `src/ragcourt/testing/demo/results.json` (with its `questions.jsonl`), made by a real
  `rank` on the bundled corpus with the default models and enough questions per category that at least one
  board names a winner. Its header says the date, the models, the machine and the ragcourt version; `demo`
  prints that line before any recorded number. It is recorded again whenever the results format, the
  bundled corpus or a default model changes; the `release` skill gets that step.
- Every recorded number is printed by the same functions `rank`, `explain` and `report` use, so the demo
  cannot show output the tool does not produce.
- **README:** the top becomes: one sentence, `pip install ragcourt && ragcourt demo`, then a real excerpt
  of the recorded run (one board, one blame), then two findings from the real runs of tutorial chapter 19
  (Ollama reading 2,048 of `bge-m3`'s advertised 8,192 tokens; `bm25` chosen on the FastAPI docs while
  scoring 0.02 on paraphrase questions), each linked to its chapter. A test checks that the excerpt is
  text of the recording's output.

## Consequences

- One command file (`commands/demo.py`), one line in `cli.py`, one data folder in `testing/`; no new
  module in `core` or `flows`. About 60 KB more in the wheel.
- Design §13.1 lists `demo`; §15 names the recording; `docs/cli.md`, tutorial chapters 2 and 14, and the
  README change.
- A recorded file can go stale: the test below fails when the format changes without a new recording.

## Risks answered

- **Numbers are measured:** they are, on the bundled corpus, by real models; every one is labelled
  recorded, with date, models and machine. Nothing is said about the user's documents.
- **Nothing happens blindly / privacy:** no model is called; no address is contacted.
- **Files:** the recording is an ordinary `results.json`, `format_version "1"`.
- **Layers, simplicity:** a command that reads with `io` and prints; no new abstraction.
- Blame, gold, generated code: untouched.

## Acceptance cases (design §16)

36. **The demo needs nothing.** With sockets blocked, `ragcourt demo` exits 0, prints the live audit, the
    recorded boards and misses under a line naming the recording's date, models and machine, and writes a
    self-contained `report.html`.
37. **The demo is real output.** The recording loads as the current `format_version`, and what `demo`
    prints for it equals what `rank`'s summary and `explain` print for the same file; the README's excerpt
    is found in that output.

## Tests

`tests/e2e/test_ac36_demo_needs_nothing.py`, `test_ac37_demo_is_real_output.py`; the wheel smoke test runs
`ragcourt demo`. The recording itself is made by hand with real models (`real-model-tests`).

## Migration and compatibility

Nothing existing changes.

## Open questions for the owner

1. The README screenshot of `report.html`: an image in the repository (about 150 KB), or text only?
2. Should `demo` open the report in the browser (`--open`), or only print its path (proposed: print only)?
