# 0001: Initial design: rank RAG stages on your own documents and blame each miss (v0.1)

## Status

`proposed` (2026-11-22), from the owner's brief ([history/0001-owner-brief.md](../history/0001-owner-brief.md)).
Waiting for the owner's acceptance; no product code is written until then. The designer's choices
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
measurement (§12); output (§13); errors (§14); tests, docs and examples (§15); 24 guarantees (§16).

Designer's choices within the brief: no core dependencies (D-003); `audit` is the first-minute result
(D-006); local servers through the same client, an in-process extra for embedders and rerankers (D-007);
measured or labelled token counts (D-008) and a fixed reference tokenization for token metrics (D-009);
the split and the paired bootstrap (D-011); the closed-book check by word overlap (D-012); `retrieval` as
one blame stage (D-014); rerankers through `/rerank` (D-015); approval by answer or hash (D-017).

### Milestones

| Milestone | Delivers | Guarantees |
|---|---|---|
| M1: audit | `types`, `errors`, the stage registry and user folder, the four native chunkers, `core/offsets`, `core/audit` with the eight checks, `io/loaders`, `io/config`, token counting with the `tokens` extra and the model table, `commands/audit`, `cli` (`audit`), the bundled corpus, examples `quickstart`, `boundaries`, `own_chunker`, `docs/audit.md` and `docs/stages.md` | 1, 2, 3, 4, 18, 22 |
| M2: rank and explain | `io/client` (chat, embeddings, `/rerank`), `io/cache`, `io/questions` (generation, filters, user questions, split, the question file), the embedders, retrievers and rerankers, the `local`, `chonkie` and `langchain` extras, `core/pipeline`, `metrics`, `stats`, `blame`, `search`, the estimate and budget, `commands/rank` and `explain`, `questions` and `cache clear`, the results file, `FakeEmbedder` and `ScriptedModel`, the remaining examples but two, `docs/questions.md`, `metrics.md`, `one-question.md`, `privacy.md`, the real-model tests | 5–17, 19, 21, 24 |
| M3: the HTML report | `io/report` HTML from the results file, `rank --html`, `report`, the audit summary in it, example `report` | 23 |
| M4: doctor | `commands/doctor`: sampling, description, recommendations, the generated chunker with approval, the subprocess runner, validation and measurement against the baselines; example `doctor` | 20 |

Each milestone ends with `scripts/check.sh` green, its guarantees passing, `design/current.md` §17
updated, the docs and the changelog in step, and a short demo for the owner on the bundled corpus.

## Consequences

- A developer gets an audit of their chunks in seconds with nothing configured, and, with a model, a
  ranking whose every number is measured on their documents with its interval, and a cause and fix for
  every miss.
- Fair comparison of chunkers rests on span gold; the price is that chunkers which add or rewrite text
  cannot be evaluated in 0.1 (§18).
- Blame is transparent and testable, and coarse: `retrieval` lumps the embedder and the retriever unless
  the search measured an alternative.
- The core has no dependencies and plain-Python scoring; very large corpora (beyond about 200k chunks) are
  slow until an optional accelerator exists.
- Question quality depends on the chat model; the filters and the drop counts make that visible, not
  better. Small local models may drop many questions (unresearched, [0000-research.md](../history/0000-research.md) §5).
- The name is crowded (D-001).

## Migration and compatibility

A new product; nothing to migrate. The question file and the results file carry `format_version "1"` from
the first release and refuse newer versions with a message; stage names, check codes and metric names
are stable from the first release (`deprecate-and-migrate`); the cache is versioned and disposable; the
public Python API is `ragdoctor` with an explicit `__all__`.

## Open questions for the owner

1. **The name** (D-001): keep `ragdoctor` despite `rag-doctor` on PyPI and two RAG-diagnosis
   `ragdoctor` repositories on GitHub, or choose another (`retrievalscope` is clear) before publishing?
2. **The first minute** (D-006): is `audit` with no model the result you meant, or must `rank` itself run
   in under a minute without a key (which would mean a bundled tiny embedder and no generated questions)?
3. **Local models** (D-007): are local OpenAI-compatible servers plus an optional in-process extra for
   embedders and rerankers what you meant by "local models"? No in-process chat model in 0.1.
4. **The closed-book filter** (D-012): word overlap by code is crude; acceptable, or should it wait until
   model judges are in scope?
5. **Generated code** (D-017): is approval by answer or exact hash, with an honest "not a sandbox", enough
   for 0.1?
6. **User questions** (D-025): must they carry a quote, and should they skip the closed-book filter?
7. **Where it lives** (D-004): `bshadmehr98/ragdoctor`, `honeworks`, or private for now?
