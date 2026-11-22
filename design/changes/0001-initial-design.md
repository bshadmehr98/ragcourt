# 0001: Initial design: rank RAG stages on your own documents and blame each miss (v0.1)

## Status

`proposed` (2026-11-22), from the owner's brief ([history/0001-owner-brief.md](../history/0001-owner-brief.md)).
Waiting for the owner's acceptance; no product code is written until then.

**Revised 2026-11-22** after the owner's first answers: the first result uses a local model (Ollama),
not the model-free audit; a model judge filters questions (the brief's exclusion of judges was wrong);
generated-code approval and user questions are accepted; the product is renamed **ragcourt** (from the
working name `ragdoctor`) and its repository goes under `bshadmehr98`. What local models can do on the
owner's machine was measured first ([history/0002-local-models.md](../history/0002-local-models.md)) and
shaped the revision. The designer's choices
inside the brief are in [decisions.md](../decisions.md); the ones marked "awaiting owner" are the questions
below.

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
measurement (§12); output (§13); errors (§14); tests, docs and examples (§15); 27 guarantees (§16).

The owner's answers: the first minute is a quick `rank` on local models (D-006); Ollama is the local
runtime (D-007); a model judge filters questions (D-012). Designer's choices: no core dependencies
(D-003); one client with an `ollama` and an `openai` dialect (D-007); token counts measured through
Ollama or a tokenizer, otherwise labelled (D-008); a fixed reference tokenization for token metrics
(D-009); the split and the paired bootstrap (D-011); `retrieval` as one blame stage (D-014); `llm`,
`endpoint` and `cross-encoder` rerankers (D-015); the judge's self-test (D-026); default models chosen by
measurement, `gemma4` on an 8 GB GPU (D-027); code rules before the judge (D-028); the first ranking in
milestone 1 (D-029).

### Milestones

| Milestone | Delivers | Guarantees |
|---|---|---|
| M1: audit and the first ranking | `types`, `errors`, the stage registry and user folder, the four native chunkers, `core/offsets`, `core/audit` with the eight checks, `io/loaders`, `io/config`, `io/client` (the `ollama` dialect), `setup`, the `ollama` embedder with measured token counts, `io/questions` (generation, code rules, the judge and its self-test, splits, the question file), `io/cache`, the `dense` retriever, `core/pipeline`, `metrics`, `stats`, `blame` (ceilings and causes), the quick run of `rank`, `cli` (`setup`, `audit`, `rank`), the bundled corpus, `FakeEmbedder`, `ScriptedModel` and a fake Ollama server, examples `quickstart`, `boundaries`, `own_chunker`, `questions`, `rank`, `docs/audit.md`, `stages.md`, `questions.md`, `privacy.md`, the first-minute real-model test | 1–13, 15, 18, 19, 21, 22, 25, 26, 27 |
| M2: the full search and explain | the `openai` dialect, the `endpoint` embedder, `bm25` and `hybrid`, the `llm`, `endpoint` and `cross-encoder` rerankers, the `tokens`, `local`, `chonkie` and `langchain` extras, `core/search` (greedy, all four steps), the estimate and budget, measured fixes, `explain`, `questions` and `cache clear`, the results file in full, the remaining examples but two, `docs/metrics.md` and `one-question.md` | 14, 16, 17, 24 |
| M3: the HTML report | `io/report` HTML from the results file, `rank --html`, `report`, the audit summary in it, example `report` | 23 |
| M4: doctor | `commands/doctor`: sampling, description, recommendations, the generated chunker with approval, the subprocess runner, validation and measurement against the baselines; example `doctor` | 20 |

Each milestone ends with `scripts/check.sh` green, its guarantees passing, `design/current.md` §17
updated, the docs and the changelog in step, and a short demo for the owner on the bundled corpus.

## Consequences

- A developer with Ollama gets, after a one-time `setup`, a first ranking of local embedders on their own
  documents in about a minute, with intervals and a cause for every miss, and the audit of their chunks in
  seconds; the full search and fixes follow with `rank --full`.
- Question filtering rests on a local judge; the self-test makes a bad judge visible and refuses it, but
  question quality still depends on the local model (measured on one corpus only so far).
- Fair comparison of chunkers rests on span gold; the price is that chunkers which add or rewrite text
  cannot be evaluated in 0.1 (§18).
- Blame is transparent and testable, and coarse: `retrieval` lumps the embedder and the retriever unless
  the search measured an alternative.
- The core has no dependencies and plain-Python scoring; very large corpora (beyond about 200k chunks) are
  slow until an optional accelerator exists.
- The first minute is an estimate (about 60 s on the owner's machine) until the end-to-end real-model test
  measures it in milestone 1.

## Migration and compatibility

A new product; nothing to migrate. The question file and the results file carry `format_version "1"` from
the first release and refuse newer versions with a message; stage names, check codes and metric names
are stable from the first release (`deprecate-and-migrate`); the cache is versioned and disposable; the
public Python API is `ragcourt` with an explicit `__all__`.

## Open questions for the owner

Answered on 2026-11-22: the name is `ragcourt` (D-001), the first result uses a
local model, Ollama, a model judge, generated-code approval, user questions, the repository under
`bshadmehr98`. Still open:

1. **Milestone 1** (D-029): it now includes the first ranking on local models (question writing, the
   judge, the default embedders, intervals, blame), not only the audit. Agreed?
2. **The judge's self-test** (D-026): refuse a judge below 90% agreement on bundled labelled cases?
3. **Default local models** (D-027): `gemma4` as question writer and judge, `nomic-embed-text`,
   `embeddinggemma` and `mxbai-embed-large` for the quick run, chosen from today's measurements?
4. **Still from the first round:** the 50/50 split with a paired bootstrap for ties (D-011), and `retrieval`
   as one blame stage (D-014).
