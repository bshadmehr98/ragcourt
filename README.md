# ragcourt

**Your RAG misses answers. ragcourt tells you which stage lost each one, and what would fix it.**

[![CI](https://github.com/bshadmehr98/ragcourt/actions/workflows/ci.yml/badge.svg)](https://github.com/bshadmehr98/ragcourt/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](https://github.com/bshadmehr98/ragcourt/blob/main/LICENSE)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![Dependencies: none](https://img.shields.io/badge/dependencies-none-brightgreen.svg)
![Runs locally](https://img.shields.io/badge/runs-locally%20with%20Ollama-black.svg)

A command-line tool that ranks chunkers, embedding models, retrievers and rerankers on **your own
documents**, with local models, and blames every missed question on one stage, by code, with the evidence.

- **Your documents, not a leaderboard's.** The best embedder on a public benchmark is often not the best
  on your text. ragcourt measures it there.
- **A cause, not only a score.** "Recall is 0.71" does not tell you what to change. "This answer was cut
  in half by the chunker" does.
- **No invented winners.** Every number has a confidence interval. When two pipelines cannot be told
  apart, it says "no significant difference".
- **Private and free to run.** Local models through Ollama. No API key, no telemetry, nothing leaves your
  machine unless you configure it.

## See it in one minute

No model, no key, no network:

```text
pip install git+https://github.com/bshadmehr98/ragcourt
ragcourt demo
```

(ragcourt 0.1 is not on PyPI yet; from its first release this is `pip install ragcourt`.)

`demo` audits a small bundled set of documents on the spot, then replays a real run recorded with local
models on a laptop. A few lines of what it prints:

<!-- demo-excerpt -->
```text
check                 recursive  fixed:size=128,overlap=0
--------------------  ---------  ------------------------
cut.mid_sentence      0 (0%)     23 (64%)
context.no_heading    1 (7%)     21 (58%)
split.table           0 (0%)     2 (6%)

d75e6294fdd4 [negation] What does the sweeper never do regarding dead jobs?
  quote (scheduling.md): Dead jobs are never deleted by the sweeper.
  cause: ranking.not_rescued, confirmed
  evidence: retrieved at rank 2, below k = 1; no reranker
  fix: a reranker that lifts it, or a larger k: with reranker llm it reaches the top k (measured in this run)
```

The table is the audit: how two chunkers cut the same text. Below it is one missed question: the stage
that lost it, the evidence, and a fix that was **measured in the same run**, not guessed. With 13 short
documents the demo names no winning pipeline, and says so: there are too few questions to tell.

## What it found on real documents

All of this was run on one laptop with an 8 GB GPU
([the real runs](https://github.com/bshadmehr98/ragcourt/blob/main/tutorial/19-real-runs.md)):

- **Ollama read 2,048 tokens of a model advertised for 8,192.** `bge-m3` was cut at a quarter of its
  length, without a word. ragcourt measures the limit in force and flags every chunk that passes it.
- **An average hid a broken retriever.** On the FastAPI docs, keyword search (`bm25`) tied for the best
  overall score while scoring 0.02 on paraphrased questions, against 0.18 for `hybrid`. The per-category
  board showed it.
- **Chunk size mattered more than the embedder.** On Chroma's chunking benchmark, 256-token chunks beat
  512-token ones by 0.15 to 0.17, while three embedders were within 0.03 of each other on 270 held-out
  questions.
- **Naive chunking cut one answer in five** before any embedder was involved (800-character chunks, the
  same benchmark).

A leaderboard as ragcourt reports it, on 25 pages of the Kubernetes docs (`=` is a tie with the top):

```text
embedders    nomic-embed-text 0.43 [0.33, 0.53]  = embeddinggemma 0.43  = mxbai-embed-large 0.36      no winner
chunkers     markdown 0.62 [0.50, 0.78]  = recursive 256 0.55  = fixed 0.50  = sentence 0.50
             recursive 512 0.43 [0.31, 0.55]  (clearly worse)                                       no winner
retrievers   bm25 0.70 [0.60, 0.78]  = hybrid 0.65;  dense 0.55 (clearly worse)                       no winner
rerankers    llm 0.80 [0.70, 0.90];  none 0.70                                                      winner: llm
```

One winner in four steps, because that is all the data supports.

## On your own documents

You need Python 3.11+ and [Ollama](https://ollama.com).

```text
ragcourt setup              # once: picks local models that fit your machine, downloads them if you agree
ragcourt audit docs/        # seconds, no chat model: how each chunker cuts your text
ragcourt rank docs/ --quick # minutes: where your documents are missed and why; names no winner
ragcourt rank docs/         # about an hour: ranks every stage with intervals (reuses the quick look's questions)
ragcourt explain            # why each missed question was missed, and what would fix it
ragcourt report             # the same as one HTML file
```

Markdown, text, reStructuredText and HTML are read as they are; PDF with the extra `pdf`
([docs/pdf.md](https://github.com/bshadmehr98/ragcourt/blob/main/docs/pdf.md)).

## Already have a retrieval system?

Keep your vector database and your framework. Wrap your system in one function, in
`ragcourt_stages/mine.py`, and ragcourt scores it on the same questions and explains its misses:

```text
from ragcourt.stages import pipeline

@pipeline("mine")
def mine(query: str, depth: int) -> list[str]:
    hits = my_index.search(query, limit=depth)   # your vector database, your framework
    return [hit.text for hit in hits]            # the chunk texts, best first
```

```text
ragcourt rank docs/ --pipeline mine              # yours beside the best pipeline ragcourt found
ragcourt rank docs/ --pipeline mine --no-search  # only yours: no embedding model is needed
```

More in [docs/stages.md](https://github.com/bshadmehr98/ragcourt/blob/main/docs/stages.md), and a runnable
version in [examples/own_pipeline.py](https://github.com/bshadmehr98/ragcourt/blob/main/examples/own_pipeline.py).

## How it works

1. **Questions with exact answers.** A local model writes test questions of six kinds (paraphrase, keyword,
   exact term, numeric, negation, distractor). Each answer is an exact quote from your text, so it does
   not depend on any chunker. A judge model, which must first pass a 40-case self-test, throws out the bad
   ones. Or bring your own questions.
2. **A search over the four stages.** Embedder, chunker, retriever, reranker: each step is chosen on one
   third of the questions and reported on the other two thirds, with bootstrap intervals, per kind of
   question.
3. **Blame by code.** For every miss, offsets, ranks, scores and probes name one cause out of 16 (cut in
   half by the chunker, drowned in a long chunk, past the embedder's input limit, exact words the embedder
   blurred, a look-alike passage, demoted by the reranker…). It is `confirmed` when another pipeline
   measured in the same run finds the answer. No model is ever asked who is to blame.

What is in the box: 9 chunkers (its own, and adapters for chonkie and LangChain splitters), embedders
through Ollama, any OpenAI-compatible endpoint or sentence-transformers, `dense`, `bm25` and `hybrid`
retrieval, LLM and cross-encoder rerankers, 8 audit checks, and one file to add your own of each. The core
installs **no dependencies**: it is the Python standard library.

**Nothing happens blindly.** Before any model is called you see which model does each job and what it is
shown; the judge's prompts and every verdict's reason are yours to read.

## What it is not

- Not an evaluator of generated answers: it measures retrieval, the part that decides what the model gets
  to read.
- Not a vector database or a framework: it runs in memory, on a folder of documents.
- Not fast on a first full run: writing hundreds of questions with a local model takes about an hour.
  `--quick` gives a first look in minutes.

## Learn it

**[The ragcourt tutorial →](https://github.com/bshadmehr98/ragcourt/blob/main/tutorial/README.md)** RAG
retrieval and ragcourt from zero, in 21 short chapters: what RAG is, every chunker, embedder, retriever and
reranker, every metric explained with a worked example, intervals and ties, why questions fail, every
command and setting, your own stages, and what we saw on real documents.

Short reference: [docs/](https://github.com/bshadmehr98/ragcourt/tree/main/docs/). Runnable examples:
[examples/](https://github.com/bshadmehr98/ragcourt/tree/main/examples/).

## Status

0.1, alpha, not yet on PyPI. Developed and tested on Linux with Ollama; Windows and macOS are not yet
proven. If ragcourt finds
something in your documents, or gets something wrong, please
[open an issue](https://github.com/bshadmehr98/ragcourt/issues). A star helps other people find it.

## How this was built

Specified by a human; designed and built by AI against a written design and tests, reviewed by a human.
The design is in [design/current.md](https://github.com/bshadmehr98/ragcourt/blob/main/design/current.md),
its history in [design/changes/](https://github.com/bshadmehr98/ragcourt/tree/main/design/changes/) and
[design/decisions.md](https://github.com/bshadmehr98/ragcourt/blob/main/design/decisions.md). Contributors:
[CONTRIBUTING.md](https://github.com/bshadmehr98/ragcourt/blob/main/CONTRIBUTING.md); AI coding tools:
[AGENTS.md](https://github.com/bshadmehr98/ragcourt/blob/main/AGENTS.md).

Security problems: privately, as
[SECURITY.md](https://github.com/bshadmehr98/ragcourt/blob/main/SECURITY.md) says. Everyone taking part
follows the [code of conduct](https://github.com/bshadmehr98/ragcourt/blob/main/CODE_OF_CONDUCT.md).

## License

Apache-2.0. Copyright 2026 Bahman Shadmehr.
