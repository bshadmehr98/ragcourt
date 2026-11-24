# 0004: A quick look: `rank --quick`

## Status

`proposed` (2026-11-24). Reopens D-034, the owner's own answer of 2026-11-22 ("no quick mode"), at the
owner's request of 2026-11-24.

## Context

A full run writes about 540 questions and took 71 minutes on the FastAPI docs on an 8 GB GPU (D-057). D-034
dropped a "first look" of 8 questions per category because "a ranking on a handful of questions per
category is noise that people would act on". That danger is real. But an hour before the first result on
one's own documents loses most new users, and since D-034 two things were built that make a short run
honest: a category under 30 held-out questions is "too few to rank" and a board made only of such
categories is **indicative**, with no winner named (§6.8, §8.4); and a larger run reuses the questions a
smaller one wrote (D-047).

`ragcourt rank DOCS --questions 20` already does all of this today. What is missing is a name for it, a
plain statement of what it can and cannot tell, and the way on to the full run.

## Problem

Give a first result on the user's own documents in minutes, without ever presenting noise as a ranking.

## Options

1. **Leave it as it is:** users who read the options find `--questions N`.
2. **Make the short run the default** and the full run a flag: faster for everyone, but the default result
   would then be the one that names no winner.
3. **A named flag, `--quick`** (chosen): the existing short run, said to be one.

## Decision

`ragcourt rank DOCS --quick` is `--questions 20` (about 120 questions: 6 or 7 dev and 13 or 14 held-out per
category) with three additions:

- **The plan says what it is** before anything is called: "A quick look: 20 questions per kind. It shows
  where the misses are and which stages clearly fail. It cannot name a winner: differences under about N
  points cannot be seen with 14 questions. The full run (about M minutes, estimated) reuses these
  questions: `ragcourt rank DOCS`."
- **No winner, by the existing rule.** Every category is too few to rank, so every board is indicative and
  names none; the smallest difference each category can tell apart is printed as always. `--quick` adds no
  new statistics and no exception to §8.4.
- **The summary ends with the way on:** the same command without `--quick`, and its estimated time given
  the questions already written.

Blame, ceilings, `explain` and the report work as in any run; the report's title says "quick look".
`--quick` with `--questions N` is a usage error (exit 2). The estimate by the measured rates of D-057: 12
minutes to write 120 questions, then embedding and about 5 minutes for the `llm` reranker step; under 20
minutes on an 8 GB GPU for a corpus the size of the FastAPI docs. It is printed in the plan, as always.

## Consequences

- One flag in `commands/rank.py`, one field in `RankOptions`, a paragraph in the plan and the summary
  (`io/rank_output.py`), a `quick` key in the plan and so in `results.json` (a new optional key).
- Design §6.8, §10.3 and §13.1; `docs/cli.md`; tutorial chapters 2, 12 and 14; the README's quick tour
  puts `--quick` first. D-034 gets a line pointing here.

## Risks answered

- **Numbers are measured:** unchanged; fewer questions give wider intervals, which are printed. No entry
  is called better without a separable difference, and with these counts none is called the winner.
- **Search on dev, report on held-out:** unchanged. With 6 dev questions per category the dev choice is
  weak; ties on dev are already reported, and the plan says the choice is provisional.
- **Files:** `quick` is a new optional key; `format_version` stays.
- **Nothing happens blindly:** the plan states the limits before the first model call.
- **Simplicity:** no new mode in the code; a preset and three sentences.
- Blame, gold, privacy, layers, generated code: untouched.

## Acceptance cases (design §16)

38. **A quick look never names a winner.** `rank --quick` prints in its plan that it cannot name one and
    why, before any model call; every board of the run is indicative with no winner; the smallest
    difference per category is printed; the summary names the full run; a following `rank` without
    `--quick` writes only the questions still missing.

## Tests

`tests/e2e/test_ac38_quick_look.py` on the bundled corpus with the scripted model; a unit test for the
usage error; the walk-through in `docs/cli.md` runs in the tests.

## Migration and compatibility

Nothing existing changes; `--questions N` stays.

## Open questions for the owner

1. **20 per category** (under 20 minutes, intervals about ±25 points per category) or **12** (about 10
   minutes, wider still)? Proposed: 20.
2. Should a quick look **skip the `llm` reranker step** unless `--rerankers` is given (saves about 5
   minutes, but then it looks at three stages, not four)? Proposed: keep all four.
