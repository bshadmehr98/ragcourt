---
name: start-task
description: Start any new piece of work (feature, fix, docs, refactor) on its own branch and decide whether it needs a change record. Use as soon as the user asks for a change, before editing any file.
---

# Start a task

1. `git status`. If there are uncommitted changes that don't belong to this task, stop and ask the user
   what to do with them.
2. `git switch main && git pull --ff-only` (skip the pull while the repository has no remote).
3. `git switch -c <type>/<short-slug>`, named as in CONTRIBUTING.md "Branches and pull requests"
   (`feat/budget-recall`).
4. Classify the task:
   - **Design change**: it changes the public API or the CLI, a guarantee in `design/current.md` §16, a
     stage kind or its signature (§7), how offsets or token counts are found (§4), an audit check (§5),
     how questions and gold quotes are made or split (§6), a metric or how uncertainty is reported (§8), a
     blame rule (§9), the search, the cache or the budget (§10), what is sent to a model (§11), doctor's
     safety steps (§12), the question or results file (§6.5, §13.3), the layers (§3.1), or adds an extra
     or a dependency. Next: `plan-change`.
   - **Small change**: a fix that restores documented behaviour, docs, tests, a refactor, a new built-in
     stage that fits its kind (`add-stage`), the look of the terminal or HTML output. Next:
     `implement-change`; a judgment call goes into `design/decisions.md`.
5. Tell the user in one or two lines: the branch, the classification, the next step.

The whole flow is in `CLAUDE.md`.
