---
name: deprecate-and-migrate
description: Change or remove public API, CLI commands or flags, stage names, audit check codes, the question file or the results file without breaking users - deprecation warnings, a compatibility period, migrations. Use when a change renames, removes or changes the meaning of anything users, their configuration or their stored files depend on.
---

# Deprecate and migrate

Users keep question sets, configuration and results across versions, and compare runs over time. Break
nothing silently.

**Public API and CLI**
1. Keep the old name working for at least one minor release: it calls the new one and warns with
   `warnings.warn("<old> is deprecated, use <new>; it will be removed in <version>", DeprecationWarning, stacklevel=2)`.
   CLI: the same message on stderr.
2. Docs and examples show only the new form. `CHANGELOG.md`: **Deprecated** now, **Removed** when it goes.
3. Tests: the old form still works and warns; the new form works.

**Stage names, audit check codes and metric names** (configuration, results and reports name them:
`recursive`, `cut.mid_sentence`, `recall_at_budget`, …)
1. A name never changes meaning and is never reused; a removed one stays reserved and is listed as retired
   in `docs/stages.md` or `docs/audit.md`. A configuration that names a retired stage fails with a message
   naming its replacement.
2. A change to how a metric is computed is a new metric name, not a silent change: old results must stay
   comparable with what they say.

**The question file and the results file** (`design/current.md` §6.5 and §13.3)
1. Both carry a `format_version`. New optional keys keep it. Removing a key or changing its meaning needs
   a new version and a change record (`plan-change`) with a "Migration and compatibility" section.
2. An older file is read (or migrated forward on read); a newer file is refused with a message that says
   which version of ragcourt reads it. Never guess.
3. Keep a small file of each old version in `tests/fixtures/` and test both the reading and the refusal
   message.
4. The embedding cache is disposable: a change to its layout bumps its version and starts a new cache;
   it never needs a migration.
