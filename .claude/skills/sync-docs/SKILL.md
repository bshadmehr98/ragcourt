---
name: sync-docs
description: Update every file a change affects - design/current.md, docs/, README, examples, CHANGELOG, AGENTS.md, the change record. Use after implementing any change and before verify-before-done; reviewers use the same table to find missing updates.
---

# Keep the docs in sync

Look at `git diff main...HEAD --stat` and the diff itself, then apply every row that matches:

| If the change... | Update |
|---|---|
| changes behaviour or the public API | `design/current.md` (the section, §16 guarantees, §17 implemented and planned), the matching `docs/*.md` page, `README.md` if the quickstart or feature list changes |
| adds or changes a CLI command or flag | `docs/cli.md` (its bash blocks run in the tests), `design/current.md` §13.1 |
| adds, removes or changes a stage | `docs/stages.md`, `design/current.md` §7.3 or §7.4 |
| adds or changes an audit check | `docs/audit.md`, `design/current.md` §5.1 |
| changes a metric, the split or the uncertainty | `docs/metrics.md`, `design/current.md` §8 |
| changes a blame rule or a suggested fix | `docs/one-question.md` (the walk-through), `design/current.md` §9 |
| changes how questions or gold quotes are made | `docs/questions.md`, `design/current.md` §6 |
| changes what is sent to a model or an endpoint | `docs/privacy.md`, `design/current.md` §11.2 |
| changes the question or the results file | `docs/questions.md` or `docs/cli.md`, `design/current.md` §6.5 or §13.3, `format_version` if needed (`deprecate-and-migrate`) |
| adds an extra or a dependency | `pyproject.toml`, the install section of `README.md`, `docs/stages.md`, the reason in `design/decisions.md` |
| adds a concept users should know | a new example (`add-example`) |
| adds, moves or renames a module | the "Layout" of `AGENTS.md`, `design/current.md` §3.2, the layers in `scripts/check_layers.py` if a top-level unit changes |
| is visible to users | `CHANGELOG.md`, top (unreleased) section: Added / Changed / Deprecated / Removed / Fixed, linking the change record |
| completes a milestone or a change record | `design/current.md` §17; the record's status: `implemented in <next version>` when it is whole |
| is a judgment call without a record | `design/decisions.md`, next `D-` number |
| changes a rule or command contributors use | `CONTRIBUTING.md`, `AGENTS.md`, and the skill in `.claude/skills/` that describes it |

Rules:
- Every `python` block in `README.md` and `docs/*.md` runs in `tests/e2e/test_docs.py`; blocks that must
  not run use a `text` or `bash` fence. Relative links must resolve (same test).
- Write for users of the product: plain words, the words of `design/current.md` §2, the style of the page
  around it, no internal notes.
- Run `uv run pytest tests/e2e -q` when done.
