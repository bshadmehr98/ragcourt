# ragcourt

Rank chunkers, embedding models, retrievers and rerankers on **your own documents**, and say which stage
caused each miss.

See it in a minute, with no model and no network:

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

The first table is the audit: how two chunkers cut the same text. The second is one missed question: the
stage that lost it, the evidence, and a fix that was **measured in the same run**, not guessed. With 13
short documents the demo names no winning pipeline, and says so: there are too few questions to tell.

Two things measuring found that no leaderboard told us
([the real runs](https://github.com/bshadmehr98/ragcourt/blob/main/tutorial/19-real-runs.md)):

- Ollama read only the first 2,048 tokens of `bge-m3`, a model advertised for 8,192, and cut the rest
  without a word. ragcourt measures the limit in force and flags every chunk that passes it.
- On the FastAPI docs, keyword search (`bm25`) tied for the best overall score while scoring 0.02 on
  paraphrased questions, against 0.18 for `hybrid`. The average hid it; the per-category board did not.

## On your own documents

Point it at a folder of documents. Using local models on your own machine, ragcourt writes test questions
whose answers are exact quotes from your text, has a judge throw out the bad ones, and ranks pipelines on
them with confidence intervals. For every question the best pipeline misses, it tells you which stage lost
it and why (cut in half by the chunker, drowned in a long chunk, past the embedder's input limit, exact
words the embedder blurred, a look-alike passage, demoted by the reranker) and what would fix it. Code does
the measuring and the blaming; no model is asked who is to blame.

## Quick tour

You need Python 3.11+ and [Ollama](https://ollama.com).

```text
ragcourt setup              # once: picks local models that fit your machine, downloads them if you agree
ragcourt audit docs/        # seconds, no chat model: how each chunker cuts your text
ragcourt rank docs/ --quick # minutes: where your documents are missed and why; names no winner
ragcourt rank docs/         # about an hour: ranks every stage with intervals (reuses the quick look's questions)
ragcourt explain            # why each missed question was missed, and what would fix it
ragcourt report             # the same as one HTML file
```

Already have a retrieval system? Wrap it in one function and `ragcourt rank docs/ --pipeline mine` scores
it on the same questions and explains its misses. PDFs: the extra `pdf` ([docs/pdf.md](https://github.com/bshadmehr98/ragcourt/blob/main/docs/pdf.md)). Also: change any model with `ragcourt models set`, add your own chunker in one file, let `ragcourt
doctor` suggest one, bring your own questions, resume long runs, set time and money budgets.

## Learn it

**[The ragcourt tutorial →](https://github.com/bshadmehr98/ragcourt/blob/main/tutorial/README.md)** RAG retrieval and ragcourt from zero, in 21 short
chapters: what RAG is, every chunker, embedder, retriever and reranker, every metric explained with a
worked example, intervals and ties, why questions fail, every command and setting, your own stages, and
what we saw on real documents (Kubernetes docs, with local models).

**Nothing happens blindly.** Before any model is called you see which model does each job and what it is
shown; the judge's prompts and every verdict's reason are yours to read. **Nothing leaves your machine**
unless you configure an endpoint. No telemetry.

## How this was built

Specified by a human; designed and built by AI against a written design and tests, reviewed by a human.
The design is in [design/current.md](https://github.com/bshadmehr98/ragcourt/blob/main/design/current.md), its history in [design/changes/](https://github.com/bshadmehr98/ragcourt/tree/main/design/changes/)
and [design/decisions.md](https://github.com/bshadmehr98/ragcourt/blob/main/design/decisions.md). Contributors: [CONTRIBUTING.md](https://github.com/bshadmehr98/ragcourt/blob/main/CONTRIBUTING.md); AI coding
tools: [AGENTS.md](https://github.com/bshadmehr98/ragcourt/blob/main/AGENTS.md).

Security problems: privately, as [SECURITY.md](https://github.com/bshadmehr98/ragcourt/blob/main/SECURITY.md)
says. Everyone taking part follows the
[code of conduct](https://github.com/bshadmehr98/ragcourt/blob/main/CODE_OF_CONDUCT.md).

## License

Apache-2.0. Copyright 2026 Bahman Shadmehr.
