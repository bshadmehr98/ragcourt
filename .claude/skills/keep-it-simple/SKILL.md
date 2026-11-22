---
name: keep-it-simple
description: Write or reshape ragcourt code so a newcomer can read it - small modules, short flat functions, plain loops over clever expressions, files instead of a database, one file per extension. Use while writing any code in src/, scripts/, tests/ or examples/, when scripts/check_simple.py or ruff's complexity rules fail, and before handing work to the reviewers.
---

# Keep it simple

The rules and limits are in CONTRIBUTING.md, "Keep it simple"; `scripts/check_simple.py` and ruff check
most of them. This is how to meet them well, not just pass the checks.

**Before writing**
1. Find the extension point in the "How it grows" table of CONTRIBUTING.md. If the change fits one, it
   is one new file (and maybe one line in a list). If it does not fit any, stop: it may be a design
   change (`plan-change`).
2. Name the module after its one concept, in the words of `design/current.md` §2. If you can't name it
   in a few words, it is two modules.
3. Data first: write the dataclass or the file format, then the functions that use it.

**While writing**
- A function does one thing its name says. Return early instead of nesting; put the happy path last
  and unindented.
- A comprehension that needs a second `for`, a second `if`, or a line break to read: write the loop.
  ```python
  # no
  spans = [(c.start, c.end) for doc in docs for c in doc.chunks if c.text if not c.flagged]
  # yes
  spans = []
  for doc in docs:
      kept = [c for c in doc.chunks if c.text and not c.flagged]
      spans += [(c.start, c.end) for c in kept]
  ```
- A conditional expression that needs an `else … if`: write `if`/`elif`. A value you compute twice or
  explain in a comment: give it a name.
- State goes in arguments and return values, never in module globals (the stage registry is the one
  exception) or in hidden files. `core` never does I/O.
- Persist with plain files the user can open (JSON, JSONL, TOML); never add a database, a server, a
  thread or `async`.
- A class only for data (`@dataclass(frozen=True)`), a `Protocol`, an enum or an error. Behaviour is a
  function.

**When a check fails**
- Too long: find the second concept in the function or module and move it out under its own name. Do
  not cut a function into `step1`, `step2` or `_helper` pieces that mean nothing alone; do not move code
  into a `utils` module.
- Too deep: return early, or turn the inner loop into a named function.
- Too many parameters: they usually travel together; make them a dataclass.
- Never silence a rule with `noqa` without a comment that says why the rule is wrong here, and tell the
  user.

**Before handing over**
- Read the diff as a newcomer would: can each new function be understood without opening another file?
  Is there a shorter, plainer version? Is anything unused?
- Run `scripts/check.sh`; the `simplicity-reviewer` agent reviews the same list.
