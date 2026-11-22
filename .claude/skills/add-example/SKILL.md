---
name: add-example
description: Add a runnable, explained example to examples/ that the tests execute. Use when a change adds a concept users should see, or the user asks for an example.
---

# Add an example

ragdoctor has no examples yet. The first one also creates its test.

1. One concept per file: `examples/<name>.py`:
   - a module docstring with a **What:**, a **How:** and a **Why:** paragraph (what it shows, the calls
     it uses in order, the problem it solves);
   - offline and fast: the bundled corpus (`tests/fixtures/corpus/`, or a few documents written inline),
     the fake embedder and the scripted model from `ragdoctor.testing`, a temporary project folder; no
     API key, no network, no model download;
   - prints a few lines that show the result and asserts the key facts.
2. List it in `examples/README.md`, in reading order (each example builds on the ones before it), with the
   section of `design/current.md` it illustrates.
3. A test in `tests/e2e/` runs every file in examples/, checks the What / How / Why docstring and that the
   file is listed (create it with the first example); run it.
4. An examples/quickstart.py is also run by `scripts/check.sh` against the built wheel alone.
5. The examples are listed in `design/current.md` §15.3; add it there too.
