# ragcourt

Rank chunkers, embedding models, retrievers and rerankers on **your own documents**, and say which stage
caused each miss.

Point it at a folder of documents. Using local models on your own machine, ragcourt writes test questions
whose answers are exact quotes from your text, has a judge throw out the bad ones, and ranks pipelines on
them with confidence intervals. For every question the best pipeline misses, it tells you which stage lost
it and why (cut in half by the chunker, drowned in a long chunk, past the embedder's input limit, exact
words the embedder blurred, a look-alike passage, demoted by the reranker) and what would fix it. Code does
the measuring and the blaming; no model is asked who is to blame.

## Install

Python 3.11 or newer, and [Ollama](https://ollama.com) for the local models.

```text
uv tool install ragcourt              # or: pip install ragcourt
ragcourt setup                        # once: checks Ollama, recommends models that fit, pulls them if you agree
```

Optional extras: `ragcourt[chonkie]` and `ragcourt[langchain]` (their chunkers), `ragcourt[tokens]`
(exact token counts for endpoints), `ragcourt[local]` (sentence-transformers embedders and cross-encoders;
brings torch).

## Use

```text
ragcourt audit docs/        # seconds, no chat model: how each chunker cuts your text
ragcourt rank docs/         # the ranking: prints its plan and time estimate first, then progress
ragcourt explain            # every missed question: stage, mechanism, evidence, fix
ragcourt rank docs/ --html  # and a self-contained report.html
ragcourt doctor docs/       # a model recommends (and may write) a chunker; everything is measured
```

A first `rank` writes about 540 questions (90 in each of six categories) and takes 15 to 25 minutes on an
8 GB GPU; it is resumable (`--resume`), and later runs reuse the questions and the cached embeddings.

What you get:

- **Leaderboards per stage**, on held-out questions, with 95% intervals; "no significant difference" when
  the top entries cannot be told apart, and the smallest difference your questions can detect.
- **Questions by kind**: different wording, keywords, exact terms, misleading questions, negations and
  numbers, reported per category, so you see which embedder fails on which kind.
- **Blame by mechanism** for every miss, `confirmed` by a measured alternative or `indicated` by probes.
- **The audit**: cut sentences, lost headings, split tables and code, repeated headers, near-duplicates,
  tiny chunks, and chunks longer than your embedder actually reads.

**Nothing happens blindly.** Before any model is called you see the plan: which model does each job, where
that choice came from, what it is shown. The judge's prompts and test cases are files you can read; every
verdict keeps its reason; `ragcourt models set ROLE MODEL` changes any model in one command.

**Nothing leaves your machine** unless you configure an endpoint: Ollama on `localhost` is the default and
any OpenAI-compatible server works when named. No telemetry. Keys are read from environment variables only.

## Try it without models

The package ships a small corpus and fakes, so you can see every output offline:

```python
import tempfile
from pathlib import Path

from ragcourt.cli import main
from ragcourt.testing import corpus_path, offline_project

with tempfile.TemporaryDirectory() as folder, offline_project(Path(folder)):
    assert main(["audit", str(corpus_path()), "--embedder", "fake", "-q"]) == 0
```

More in [examples/](examples/README.md); the documentation is in [docs/](docs/README.md).

## How this was built

Specified by a human; designed and built by AI against a written design and tests, reviewed by a human.
The design is in [design/current.md](design/current.md), its history in [design/changes/](design/changes/)
and [design/decisions.md](design/decisions.md). Contributors: [CONTRIBUTING.md](CONTRIBUTING.md); AI coding
tools: [AGENTS.md](AGENTS.md).

## License

Apache-2.0. Copyright 2026 Bahman Shadmehr.
