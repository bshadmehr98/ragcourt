---
name: plan-change
description: Plan a design change as a change record in design/changes/ and get it approved before writing code. Use after start-task when a change touches the public API, the CLI, a guarantee, a stage kind or its signature, a metric or a blame rule, the question or results file, what is sent to a model, the layers, extras or dependencies.
---

# Plan a design change

1. Read `design/current.md` (§1 goals and non-goals, the sections the change touches, §16 guarantees),
   `design/decisions.md` and the related records in `design/changes/`.
2. Next number: the highest `design/changes/NNNN-*.md` plus one.
3. Write `design/changes/NNNN-<short-name>.md` in the format of the existing records (for example
   `design/changes/0001-initial-design.md`): Status `proposed`, Context, Problem, Options (at least two,
   one of them "leave it as it is"), Decision, Consequences, Migration and compatibility. Include:
   - a sketch of the public API, the CLI or the output as a user would meet it;
   - the new or changed acceptance cases, numbered after the last one in `design/current.md` §16;
   - the tests that will prove it (unit, e2e on the bundled corpus, a real model if a model-backed stage
     changes).
4. Answer each risk the change touches, in the record:
   - **numbers are measured** (§8): a new metric says how it is computed, on which split, with which
     uncertainty; nothing is reported as better without a measurement that says so;
   - **blame stays code** (§9): a new or changed rule is computed from offsets and ranks, never by a
     model, and still gives each miss exactly one stage;
   - **gold stays independent of chunking** (§6): questions and quotes never depend on a chunker;
   - **the layers hold** (§3.1): stages never import each other; core stays pure; the import check
     passes;
   - **privacy** (§11.2): nothing new leaves the machine unless the user configured that endpoint; no
     telemetry; no document text in logs;
   - **files** (§6.5, §13.3): new optional keys keep the `format_version`; anything else follows
     `deprecate-and-migrate`; stage names and check codes never change meaning;
   - **nothing happens blindly** (§6.6, §10.3, §11.4): a new model call or verdict is shown to the user
     in the plan, with its prompt readable and its reasons kept;
   - **generated code** (§12): nothing a model wrote runs without the user's approval, outside a
     subprocess with a timeout, or unvalidated;
   - **the core imports no extra**; a new dependency is an optional extra with a reason in
     `design/decisions.md`;
   - **simplicity** (CONTRIBUTING.md, "Keep it simple"): does the change fit an extension point of "How it
     grows" (one new file)? Does it add a dependency, a database, a thread, a class hierarchy or a new
     kind of configuration? Is there a smaller option that meets the need?
5. Commit: `docs(design): propose NNNN <short name>`.
6. **Stop and ask.** Give the user the decision and the open questions in a few lines, with the file
   path. Only the project's maintainer accepts a record. If the user is the maintainer and approves, set
   the status to `accepted (approved by the maintainer YYYY-MM-DD)`, commit, and continue with
   `implement-change`. Otherwise the status stays `proposed`: offer to open a pull request with the record
   alone, and open it (`open-pr`) only when the user says so (AGENTS.md rule 10); or link the record from
   the issue. The maintainer decides there. On rejection set `rejected` with the reason and stop.
