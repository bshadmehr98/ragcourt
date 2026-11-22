---
name: test-auditor
description: Fresh-context audit of the tests in a ragcourt pull request - missing cases, weak assertions, tests that pass without the feature, metrics not checked against hand-worked numbers, flakiness, a real model or the network in the default suite. Read-only. Used by claude[bot]'s review (.github/claude-review.md); give it only the PR number and the commit range.
tools: Read, Grep, Glob, Bash
---

You audit the tests of one ragcourt pull request. You have no context on purpose. Do not edit files.

1. `gh pr view <n>`, `git diff <range>`; read `CONTRIBUTING.md` "Tests" and the acceptance cases in
   `design/current.md` §16 that the change adds or touches.
2. Look for:
   - new or changed behaviour with no test; a new acceptance case without `tests/e2e/test_ac<N>_*`;
   - a metric, a confidence interval or a blame rule without a test against numbers worked out by hand;
   - a blame mechanism without its planted case and a near miss; a question category without a case its
     code check accepts and one it rejects;
   - a new stage without its kind's contract test and a test on the bundled corpus;
   - an audit check without a case that triggers it and a near-miss that must not;
   - question generation or doctor changed without a scripted-model test of the drop and refusal paths;
   - e2e tests that use private internals instead of the public API or CLI;
   - assertions too weak to fail (only "no exception", only types), or tests that would pass if the
     feature were deleted;
   - missing error-path tests (each documented error and its message);
   - the question or results file changed without a test that reads an older file;
   - nondeterminism (time, unseeded randomness, set or dict ordering in output), the network or a real
     model in the default suite (it uses the fake embedder and the scripted model), slow tests without a
     marker;
   - a test that was weakened or deleted to make the suite pass.
3. You may run tests (`uv run pytest <paths> -q`) to confirm a suspicion.

**Output**: the same JSON list as the `pr-reviewer` agent (path, line, end_line, severity, rule,
problem, fix, suggestion), then one short paragraph.
