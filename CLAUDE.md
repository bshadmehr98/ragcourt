@AGENTS.md

## Claude Code

Every task follows one flow. Each step is a skill in `.claude/skills/`:

```text
new task      -> start-task (branch) -> design change? plan-change, then wait for approval
              -> implement-change (tests first) -> sync-docs -> verify-before-done
"push" / "ship it" / "I'm happy"
              -> open-pr -> claude[bot] reviews it on GitHub
answers on GitHub -> address-review -> push -> claude[bot] reviews the new commits
merged        -> finish-task
```

- Never edit on `main`: `.claude/hooks/guard-main.sh` blocks the Edit/Write tools on this repository's
  files there (`RAGCOURT_ALLOW_MAIN=1` overrides it). Shell edits and commits are not blocked, so start
  every task with `start-task`.
- Reviews run on GitHub: `.github/workflows/claude-review.yml` has claude[bot]
  follow `.github/claude-review.md` with the reviewer agents on every push to a pull request. A branch
  pushed without a pull request gets a reminder from `.claude/hooks/after-push.sh`.
- Write all code with `keep-it-simple` (CONTRIBUTING.md "Keep it simple"); `scripts/check_simple.py` and
  ruff enforce most of it, the `simplicity-reviewer` agent the rest.
- More skills: `debug-failure`, `add-example`, `add-stage`, `deprecate-and-migrate`,
  `real-model-tests`, `triage-issue`, `learn-from-reviews`, and `release` (only when the maintainer asks).
- Reviewer agents in `.claude/agents/`: `pr-reviewer`, `test-auditor`, `simplicity-reviewer`.
  claude[bot] runs them on every pull request; run them locally only when the user asks (give each the
  branch's commit range).
- Recommended plugins, enabled in `.claude/settings.json`; install them once with
  `/plugin install pyright-lsp@claude-plugins-official` and
  `/plugin install pr-review-toolkit@claude-plugins-official`.
- `.claude/settings.json` (JSON, so it can't hold comments): `uv run *`, `scripts/check.sh` and the
  everyday read-only `git` and `gh` commands are allowed without asking; `uv publish` and `twine` are
  denied. The deny rules are a reminder, not a lock: `uv run` can start anything. To be asked before
  commands run, override `permissions` in `.claude/settings.local.json`.
- "The user" in the skills is the person in the session; "the maintainer" is whoever maintains
  ragcourt. Only the maintainer accepts change records, merges and releases.
- Settings for your machine (the `RAGCOURT_TEST_*` variables of `real-model-tests`, an endpoint key,
  extra permissions) go in `.claude/settings.local.json`, which is not committed.
