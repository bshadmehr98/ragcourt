# Learn ragcourt

Everything ragcourt can do, one short lesson at a time. Each lesson is a command or two and what you get.
Reference pages with every detail are in [docs/](docs/README.md).

1. [Install](#1-install)
2. [Try it without models](#2-try-it-without-models)
3. [Audit your chunks](#3-audit-your-chunks)
4. [Write test questions](#4-write-test-questions)
5. [Rank your pipelines](#5-rank-your-pipelines)
6. [See why questions were missed](#6-see-why-questions-were-missed)
7. [Change a model](#7-change-a-model)
8. [Add your own chunker](#8-add-your-own-chunker)
9. [Let a model suggest a chunker](#9-let-a-model-suggest-a-chunker)
10. [Bring your own questions](#10-bring-your-own-questions)
11. [Long runs, budgets and the cache](#11-long-runs-budgets-and-the-cache)
12. [Settings](#12-settings)
13. [What stays on your machine](#13-what-stays-on-your-machine)

## 1. Install

You need Python 3.11+ and [Ollama](https://ollama.com).

```text
pip install ragcourt
ragcourt setup
```

`setup` checks Ollama, picks models that fit your machine, shows their sizes and downloads them only if
you say yes. It writes `ragcourt.toml` and tests the judge model.

## 2. Try it without models

ragcourt ships a small set of documents and fake models, so you can see every output first:

```python
import tempfile
from pathlib import Path

from ragcourt.cli import main
from ragcourt.testing import corpus_path, offline_project

with tempfile.TemporaryDirectory() as folder, offline_project(Path(folder)):
    assert main(["audit", str(corpus_path()), "--embedder", "fake", "-q"]) == 0
```

The [examples](examples/README.md) run every lesson below the same way.

## 3. Audit your chunks

```text
ragcourt audit docs/
ragcourt audit docs/ --chunker "recursive:size=256,overlap=32" --show guide.md
```

In seconds, with no chat model, you see how each chunker cuts your text: sentences cut in half, chunks
without their heading, split tables and code, repeated headers, near-duplicates, tiny chunks and chunks
longer than your embedding model reads. `--show` marks the cuts on one document. In CI,
`--fail-on split.table` exits 3 when that check fires.

## 4. Write test questions

```text
ragcourt questions docs/
ragcourt questions show --dropped
```

A local model writes questions whose answers are exact quotes from your documents, in six kinds:
different wording, keywords, exact terms, misleading, negation and numbers. A judge model drops bad ones
and those a model could answer without your documents. Every drop keeps its reason. `rank` does this step
for you, so you rarely run it alone.

## 5. Rank your pipelines

```text
ragcourt rank docs/
```

It prints its plan first (which model does what, how long it will take) and asks before starting. Then it
finds the best embedder, chunker, retriever and reranker, one stage at a time, and shows a leaderboard for
each with 95% intervals. When two entries cannot be told apart it says **no significant difference**
instead of naming a winner. The first run takes 15 to 25 minutes on an 8 GB GPU; later runs reuse the
questions and the embeddings.

Compare only what you want: `--embedders nomic-embed-text,bge-m3`, `--chunkers "markdown;sentence:size=200"`,
`--retrievers dense,hybrid`, `--rerankers llm`.

## 6. See why questions were missed

```text
ragcourt explain
ragcourt explain --show QUESTION-ID
ragcourt report
```

For every question the best pipeline missed: the stage and the reason (cut by the chunker, past the
embedder's limit, drowned in a long chunk, exact words blurred, a look-alike passage, pushed down by the
reranker…), the evidence, and what would fix it. `confirmed` means ragcourt measured the fix in this run;
`indicated` means the evidence points to it. `--show` displays the quote among the chunk cuts; `report`
writes one HTML file you can share.

## 7. Change a model

```text
ragcourt models
ragcourt models set judge qwen3:4b
ragcourt models set embedders nomic-embed-text,bge-m3
ragcourt rank docs/ --judge gemma4
```

`models` shows each role (writer, judge, embedders, reranker, doctor), its model and where that choice came
from. `set` edits `ragcourt.toml` and tests a new judge at once; a flag changes a model for one run.
`ragcourt prompts show judge.validity` prints exactly what the judge is asked.

## 8. Add your own chunker

Put a file in `ragcourt_stages/`:

```text
from ragcourt.stages import chunker

@chunker("by_paragraph")
def by_paragraph(text: str, min_chars: int = 200) -> list[str]:
    return [part for part in text.split("\n\n") if len(part) >= min_chars]
```

Now `ragcourt audit docs/` and `ragcourt rank docs/ --chunkers "by_paragraph:min_chars=400"` use it.
Embedders, retrievers and rerankers work the same way (`@embedder`, `@retriever`, `@reranker`).

## 9. Let a model suggest a chunker

```text
ragcourt doctor docs/
ragcourt doctor docs/ --approve SHA256
```

A model looks at samples of your documents, recommends built-in chunkers and may write a new one. Its code
is shown with a SHA-256 and runs only if you answer yes or pass that exact hash. Everything it suggests is
measured against the built-in chunkers and called better only when the numbers say so.

## 10. Bring your own questions

```text
ragcourt rank docs/ --questions-file mine.jsonl
```

One JSON object per line: `{"question": "…", "quote": "exact text from your documents"}`, plus
`"document": "guide.md"` when the quote appears in more than one place. Your questions are never dropped
by the judge.

## 11. Long runs, budgets and the cache

- `--resume` continues a run that was stopped; nothing finished is redone.
- `--budget-minutes 30` and `--budget-usd 2` stop a run before it goes over (exit code 4).
- `--yes` starts without asking, for scripts.
- `--html` writes the report at the end of `rank`.
- `ragcourt cache clear` deletes the cached embeddings.

## 12. Settings

Everything is optional in `ragcourt.toml`:

```text
[models]
judge = "gemma4"
embedders = ["nomic-embed-text", "bge-m3"]

[questions]
per_category = 90

[search]
chunkers = ["recursive:size=512,overlap=64", "markdown"]
k = 5

[endpoints.openai]
base_url = "https://api.openai.com/v1"
api_key_env = "OPENAI_API_KEY"
```

A misspelled setting is an error that lists the right ones. Name an endpoint model as
`endpoint:openai/text-embedding-3-small`.

## 13. What stays on your machine

Everything, unless you configure an endpoint: Ollama on `localhost` is the only address ragcourt contacts.
Keys come only from environment variables and are never written down. ragcourt keeps its files in
`.ragcourt/` next to where you run it; don't commit that folder for private documents.
