---
name: implement-change
description: Build an accepted change record or a small change test-first, then update the docs and verify. Use after plan-change is approved, or directly for fixes, refactors, tests and docs work.
---

# Implement a change

1. Re-read the accepted change record (if any) and the `design/current.md` sections it changes.
2. **Tests first.** Write the tests and watch them fail for the expected reason:
   - each new acceptance case as `tests/e2e/test_ac<N>_<slug>.py`, public API or CLI only, on the bundled
     corpus with the fake embedder and the scripted model; it must fail if the feature is removed;
   - unit tests for edge cases and each error path; a contract test (`tests/contract/`) if a stage kind's
     contract or the model client changed;
   - a metric or a blame rule gets a test against numbers worked out by hand in the test;
   - for a bug: a test that reproduces it (`debug-failure`).
3. **Implement** the smallest code that passes, following `keep-it-simple` (CONTRIBUTING.md "Keep it
   simple": small modules, short flat functions, plain loops, plain files, one file per extension) and
   "Code conventions": the layers of `design/current.md` §3.1 (`scripts/check_layers.py`); `core` stays pure
   functions; errors are `RagCourtError` subclasses from `src/ragcourt/errors.py` with messages that say
   what to do; nothing reaches the network except through the one client, and only to an endpoint the user
   configured (§11.2).
4. Fast loop while working: `uv run pytest -x -q <paths>`, `uv run ruff check .`, `uv run pyright`,
   `uv run python scripts/check_layers.py`, `uv run python scripts/check_simple.py`.
5. Commit each green step as a small Conventional Commit; the body says why.
6. Run `sync-docs`, then `verify-before-done`.
7. Report to the user: what changed, which tests prove it, anything left open. Then wait for
   "push" / "ship it" / "I'm happy", which starts `open-pr`.
