# ragcourt

Rank chunkers, embedding models, retrievers and rerankers on **your own documents**, and say which stage
caused each miss.

Point it at a folder of documents. Using local models on your own machine, ragcourt writes test questions
whose answers are exact quotes from your text, has a judge throw out the bad ones, and ranks pipelines on
them with confidence intervals. For every question the best pipeline misses, it tells you which stage lost
it and why (cut in half by the chunker, drowned in a long chunk, past the embedder's input limit, exact
words the embedder blurred, a look-alike passage, demoted by the reranker) and what would fix it. Code does
the measuring and the blaming; no model is asked who is to blame.

## Quick tour

You need Python 3.11+ and [Ollama](https://ollama.com).

```text
pip install ragcourt
ragcourt setup              # once: picks local models that fit your machine, downloads them if you agree
ragcourt audit docs/        # seconds, no chat model: how each chunker cuts your text
ragcourt rank docs/         # shows its plan first, then ranks every stage with intervals
ragcourt explain            # why each missed question was missed, and what would fix it
ragcourt report             # the same as one HTML file
```

Also: change any model with `ragcourt models set`, add your own chunker in one file, let `ragcourt
doctor` suggest one, bring your own questions, resume long runs, set time and money budgets.

**[Learn ragcourt: the tutorial →](TUTORIAL.md)** Every feature in thirteen short lessons.

**Nothing happens blindly.** Before any model is called you see which model does each job and what it is
shown; the judge's prompts and every verdict's reason are yours to read. **Nothing leaves your machine**
unless you configure an endpoint. No telemetry.

## How this was built

Specified by a human; designed and built by AI against a written design and tests, reviewed by a human.
The design is in [design/current.md](design/current.md), its history in [design/changes/](design/changes/)
and [design/decisions.md](design/decisions.md). Contributors: [CONTRIBUTING.md](CONTRIBUTING.md); AI coding
tools: [AGENTS.md](AGENTS.md).

## License

Apache-2.0. Copyright 2026 Bahman Shadmehr.
