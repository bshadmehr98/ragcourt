# Why ragdoctor exists

> Point it at your documents. Using local models on your own machine, it writes questions whose answers
> are exact quotes from your text, has a judge throw out the bad ones, and ranks chunkers, embedding
> models, retrievers and rerankers on them, with intervals. For every question your pipeline misses it
> says which stage lost it and what would have found it, and it shows where your chunker cuts your text
> badly. Code does the measuring and the blaming.

**Status:** the design ([changes/0001](changes/0001-initial-design.md)) is proposed (2026-11-22, from the
owner's brief in [history/0001-owner-brief.md](history/0001-owner-brief.md)), revised after the owner's
first answers, and waits for the owner;
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
- **Evaluation needs a key.** Most tools start with a hosted model and an API key, and send the documents
  away.

## The core ideas

1. **Local first.** Ollama on the user's machine writes the questions, judges them and embeds the chunks;
   a first ranking arrives in about a minute with no key, and nothing leaves the machine.
2. **Gold is a span of the source.** A model writes a question and an exact quote; the quote must be
   found verbatim, so gold never depends on a chunker and every chunker is judged on the same questions.
   A judge, which must first pass a self-test, drops questions that are invalid or answerable from memory.
3. **Audit by code.** The most common chunking problems (cut sentences, lost headings, split tables,
   boilerplate, oversized chunks) are found in seconds, with sizes in the embedder's own tokens.
4. **Measured, on held-out questions, with intervals.** Choose on one half, report on the other; say "no
   significant difference" when that is the truth; measure recall within a token budget so size cannot
   win.
5. **Blame is arithmetic.** Not in any chunk: the chunker. Not in the top 50: retrieval. In the top 50
   but below k: ranking. Each stage's ceiling shows how much it costs.
6. **A stage is one file.** Four kinds, one decorator each, the user's own folder loaded the same way.
7. **Models are visible.** One client for Ollama and any OpenAI-compatible endpoint, nothing sent
   elsewhere without configuration, a printed estimate and a budget; generated code is shown, approved,
   isolated and measured.

## Non-goals (0.1)

Answer generation and judging answers, vector databases, images, audio, video, a hosted service, telemetry.

## What is in this folder

| File | What it holds |
|---|---|
| [`current.md`](current.md) | the design as it stands: concepts, rules, the guarantees the tests check, what is implemented |
| [`changes/0001-initial-design.md`](changes/0001-initial-design.md) | the first design, from the owner's brief (proposed), with its milestones and open questions |
| [`history/0001-owner-brief.md`](history/0001-owner-brief.md) | the owner's brief, word for word |
| [`history/0000-research.md`](history/0000-research.md) | what exists already (AutoRAG, Chroma's chunking study, chunkvet, ragblame, Ragas and others), the name checks, what is still to research |
| [`history/0002-local-models.md`](history/0002-local-models.md) | local models measured on the owner's machine: embedders, question writers, judges, the first-minute estimate |
| [`decisions.md`](decisions.md) | the owner's answers and the designer's choices, each open to review |

## How this is being built

Specified by a human; designed and built by AI against a written design and tests; every decision is
reviewed by a human. The design history is in [changes/](changes/) and [decisions.md](decisions.md); the
process is in [`../CONTRIBUTING.md`](../CONTRIBUTING.md).
