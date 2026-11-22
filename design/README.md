# Why ragdoctor exists

> Point it at your documents. It shows you where your chunker cuts them badly, without any model. Give
> it a model and it ranks chunkers, embedding models, retrievers and rerankers on questions whose answers
> are exact quotes from your own text, with intervals, and tells you, for every question your pipeline
> misses, which stage lost it and what would have found it. Code does the measuring and the blaming.

**Status:** the design ([changes/0001](changes/0001-initial-design.md)) is proposed (2026-11-22, from the
owner's brief in [history/0001-owner-brief.md](history/0001-owner-brief.md)) and waits for the owner;
[current.md](current.md) §17 says what is implemented (nothing yet).

## The problem

- **Choices are made from someone else's data.** Chunk size, embedding model, hybrid or not, which
  reranker: decided from public leaderboards and blog posts, not from the documents the system will
  serve.
- **Misses have no cause.** When the right passage does not come back, it is unclear whether the chunker
  cut it in half, the embedder never found it, or the reranker pushed it down, so people tune the wrong
  stage.
- **Chunkers can't be compared fairly.** Gold answers tied to chunk ids change with the chunker; scores
  that reward retrieving more text let big chunks win by size.
- **Numbers without error bars.** A two-point difference on forty questions is reported as a winner.
- **Evaluation needs a key and a judge.** Most tools start with an API key and a model grading answers.

## The core ideas

1. **Audit first, no model.** The most common problems (cut sentences, lost headings, split tables,
   boilerplate, oversized chunks) are visible in seconds by code.
2. **Gold is a span of the source.** A model writes a question and an exact quote; the quote must be
   found verbatim, so gold never depends on a chunker and every chunker is judged on the same questions.
3. **Measured, on held-out questions, with intervals.** Choose on one half, report on the other; say "no
   significant difference" when that is the truth; measure recall within a token budget so size cannot
   win.
4. **Blame is arithmetic.** Not in any chunk: the chunker. Not in the top 50: retrieval. In the top 50
   but below k: ranking. Each stage's ceiling shows how much it costs.
5. **A stage is one file.** Four kinds, one decorator each, the user's own folder loaded the same way.
6. **The model is optional and visible.** One client, the user's endpoint or a local server, nothing
   sent without configuration, a printed estimate and a budget; generated code is shown, approved,
   isolated and measured.

## Non-goals (0.1)

Answer generation, model judges, vector databases, images, audio, video, a hosted service, telemetry.

## What is in this folder

| File | What it holds |
|---|---|
| [`current.md`](current.md) | the design as it stands: concepts, rules, the guarantees the tests check, what is implemented |
| [`changes/0001-initial-design.md`](changes/0001-initial-design.md) | the first design, from the owner's brief (proposed), with its milestones and open questions |
| [`history/0001-owner-brief.md`](history/0001-owner-brief.md) | the owner's brief, word for word |
| [`history/0000-research.md`](history/0000-research.md) | what exists already (AutoRAG, Chroma's chunking study, chunkvet, ragblame, Ragas and others), the name check, what is still to research |
| [`decisions.md`](decisions.md) | the owner's answers and the designer's choices, each open to review |

## How this is being built

Specified by a human; designed and built by AI against a written design and tests; every decision is
reviewed by a human. The design history is in [changes/](changes/) and [decisions.md](decisions.md); the
process is in [`../CONTRIBUTING.md`](../CONTRIBUTING.md).
