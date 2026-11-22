# 0001: Initial design: rank RAG stages on your own documents and blame each miss (v0.1)

## Status

`implemented` (2026-11-22, unreleased): accepted by the owner with D-032, D-033, D-035 and D-036, and built
in the milestone below; proposed the same day from the owner's brief
([history/0001-owner-brief.md](../history/0001-owner-brief.md)). Choices made while building are D-037 to
D-055.

**Revised 2026-11-22** after the owner's first answers: the first result uses a local model (Ollama),
not the model-free audit; a model judge filters questions (the brief's exclusion of judges was wrong);
generated-code approval and user questions are accepted; the product is renamed **ragcourt** (from the
working name `ragdoctor`) and its repository goes under `bshadmehr98`. What local models can do on the
owner's machine was measured first ([history/0002-local-models.md](../history/0002-local-models.md)) and
shaped the revision. The designer's choices
inside the brief are in [decisions.md](../decisions.md), next to the owner's answers.

## Context

On 2026-11-22 the owner set this repository up in the shape of k8s-holmes and gave the brief: an
open-source Python command-line tool that ranks chunkers, embedding models, retrievers and rerankers on
the user's own documents and says which stage caused each miss, with four commands (`audit`, `rank`,
`explain`, `doctor`), gold answers as verbatim quotes, blame computed by code, intervals and ties,
greedy search by stage, four stage kinds with a decorator registry, one model client, strict import
layers, and an offline default test suite.

The survey ([history/0000-research.md](../history/0000-research.md)) found the pieces but not the whole:
Chroma's report introduced verbatim-excerpt gold and token IoU for chunkers; AutoRAG searches greedily by
node but ties gold to chunk ids; chunkvet audits chunks without a model; ragblame (two weeks old) blames
stages with quote gold but needs a model for every run and judges answers; MTCB and chunk-bench rank
chunkers on fixed or keyword gold. None ranks all four stages on the user's documents with
chunk-independent gold, intervals and code-computed blame, starting with no API key.

## Problem

Choosing a chunker, an embedding model, a retriever and a reranker is mostly done from blog posts and
public leaderboards that were not measured on the user's documents. When a RAG system misses, nobody can
say whether the chunker cut the answer in half, the embedder never found it, or the reranker pushed it
down, so people change the wrong stage. Existing evaluators score one pipeline, need a model judge and a
key, or tie gold to one chunking and cannot compare chunkers fairly.

## Options

1. **Leave it as it is:** Ragas or a notebook per project; advice from public benchmarks.
2. **A wrapper over existing evaluators** (Ragas, AutoRAG): quick, but inherits model judges, gold tied
   to chunk ids and dependencies the brief rules out.
3. **A model-driven diagnoser** (ragblame's shape): flexible explanations, but every run needs a key,
   blame is a model's opinion, and nothing is ranked with intervals.
4. **A small measuring tool** (chosen): gold as verbatim spans independent of chunking, every number
   computed by code on a held-out split with intervals, blame from spans and ranks, a greedy search with a
   cache and a budget, the standard library in the core, a model only to write questions and doctor's
   suggestions.

## Decision

Option 4, as described in [design/current.md](../current.md): concepts (§2); one package in strict
layers with a checked import rule (§3); documents, offsets found by code and token counts in the
embedder's tokens (§4); the model-free audit with eight checks (§5); questions with verbatim quotes,
filters, user questions and a dev/held-out split (§6); four stage kinds, one file each, registered by
decorator, with native stages and thin adapters as extras (§7); the pipeline, relevance, metrics and
intervals with ties (§8); blame, ceilings and measured fixes (§9); greedy search, the cache, the estimate
and the budget (§10); one model client and privacy (§11); doctor with approval, isolation, validation and
measurement (§12); output (§13); errors (§14); tests, docs and examples (§15); 33 guarantees (§16).

The owner's answers: the first result uses local models (D-006); Ollama is the local
runtime (D-007); a model judge filters questions (D-012). Designer's choices: no core dependencies
(D-003); one client with an `ollama` and an `openai` dialect (D-007); token counts measured through
Ollama or a tokenizer, otherwise labelled (D-008); a fixed reference tokenization for token metrics
(D-009); the split and the paired bootstrap (D-011); `retrieval` as one blame stage (D-014); `llm`,
`endpoint` and `cross-encoder` rerankers (D-015); the judge's self-test (D-026); default models chosen by
measurement, `gemma4` on an 8 GB GPU (D-027); code rules before the judge (D-028); the first ranking in
milestone 1 (D-029).

After the second round: milestone 1 is the whole project (D-029); nothing happens blindly, so every model
role, prompt, judge verdict and rule is shown to the user in plain words (D-030); changing a model is one
command (D-031).

After the third round: questions come in six categories aimed at known weaknesses, 90 each, reported per
category (D-032, tried in [history/0003-question-categories.md](../history/0003-question-categories.md));
blame names a stage and one of fourteen mechanisms with its evidence and whether a measurement confirms
it (D-033).

After the fourth round: no one-minute answer; the full run shows its plan and time first, then its
progress, and resumes after an interruption (D-034, D-035). No database: everything is a plain file,
the embedding cache included (D-016). Code stays simple by rules the gate checks, a working checklist
(the `keep-it-simple` skill) and a layout where every extension is one new file (D-036).

### Milestone

One milestone, the whole of 0.1 (owner, D-029), built on one branch in this order, each step with its
tests and its commits:

| Step | Builds | Guarantees it makes pass |
|---|---|---|
| 1. Foundations | `types`, `errors`, the stage registry and the user's folder, `io/documents`, `io/config`, the bundled corpus, `FakeEmbedder`, `ScriptedModel` | 18, 22 |
| 2. Audit | the four native chunkers, `core/offsets`, `core/audit` with the eight checks, `commands/audit` | 1, 2, 3 |
| 3. Local models | `io/client` (`ollama` dialect, a fake Ollama server for tests), the `ollama` embedder with measured token counts, `setup`, `models`, `prompts`, `ragcourt.toml` with roles | 4, 19, 27, 30 |
| 4. Questions and the judge | `io/questions`: the six categories with their passage rules and code checks, generation, code rules, the judge with its prompts, labelled cases and self-test, the explanations of §6.6, user questions, splits, the question file, `questions show` | 5, 6, 7, 8, 25, 29, 31 |
| 5. The first ranking | `io/cache`, the `dense` retriever, `core/pipeline`, `metrics`, `stats` (per category, overall, smallest difference), `blame` with the chunker and embedder mechanisms and the probes, the plan, progress and resume, `rank`, the legend | 9, 10, 11, 12, 15, 26, 28, 32 |
| 6. The full search and explain | the `openai` dialect, the `endpoint` embedder, `bm25` and `hybrid`, the `llm`, `endpoint` and `cross-encoder` rerankers, the `tokens`, `local`, `chonkie` and `langchain` extras, `core/search`, the estimate and budget, the retriever and ranking mechanisms, evidence levels and fixes, `explain`, the results file in full | 13, 14, 16, 17, 21, 33 |
| 7. The HTML report | `io/report` HTML, `rank --html`, `report` | 23 |
| 8. Doctor | `commands/doctor`: sampling, description, recommendations, the generated chunker with approval, the subprocess runner, validation and measurement | 20 |
| 9. Docs and examples | every page of `docs/` (with `judge.md`, `models.md` and the walk-through), every example, the README quickstart | 24 |

The milestone ends with `scripts/check.sh` green, all 33 guarantees passing, a full run timed on the
reference machine, the reviewer agents run on the branch, `design/current.md` §17 updated, the
changelog in step, and one demo for the owner on the bundled corpus and a corpus of the owner's choice.

## Consequences

- A developer with Ollama gets, after a one-time `setup`, the audit of their chunks in seconds and, in
  15 to 25 minutes on a GPU like the owner's (once per corpus, resumable), a ranking of every stage on about
  540 questions in six categories, with intervals and a stage and a mechanism for every miss.
- Question filtering rests on a local judge; the self-test makes a bad judge visible and refuses it, but
  question quality still depends on the local model (measured on one corpus only so far).
- Fair comparison of chunkers rests on span gold; the price is that chunkers which add or rewrite text
  cannot be evaluated in 0.1 (§18).
- Blame is transparent and testable: a stage and one of fourteen mechanisms, from spans, ranks and probes;
  a blame that no measured alternative confirms is labelled `indicated`.
- The core has no dependencies and plain-Python scoring; very large corpora (beyond about 200k chunks) are
  slow until an optional accelerator exists.
- The 15 to 25 minutes is an estimate (`inferred`) until the end-to-end real-model test times a full run
  in milestone 1.

## Migration and compatibility

A new product; nothing to migrate. The question file and the results file carry `format_version "1"` from
the first release and refuse newer versions with a message; stage names, check codes and metric names
are stable from the first release (`deprecate-and-migrate`); the cache is versioned and disposable; the
public Python API is `ragcourt` with an explicit `__all__`.

## Open questions for the owner

Answered on 2026-11-22: the name `ragcourt` (D-001); local models through Ollama (D-006, D-007); a model
judge (D-012) with an explained self-test (D-026, D-030); generated-code approval (D-017); user questions
(D-025); the repository under `bshadmehr98` (D-004); one milestone (D-029); the default models, easy to
change (D-027, D-031); choosing and reporting on different questions, many of each kind (D-011); a better
blame than one `retrieval` stage (D-014); no one-minute answer (D-034); no database (D-016).
Accepted on 2026-11-22 with the rest of the design: the six question categories, 90 each (D-032); blame
by stage and mechanism (D-033); progress and resume (D-035); the simplicity rules and the small-module
layout (D-036). Nothing is open.
