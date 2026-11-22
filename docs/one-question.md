# One question, from its document to its blame

This page follows one question through a run on the bundled corpus, with the scripted writer and judge
and the fake embedders standing in for local models (so the output is the same on every machine). The
code below produces the output shown after it; the documentation tests run it and check it still does.

```python
import contextlib
import io
import json
import tempfile
from pathlib import Path

from ragcourt.cli import main
from ragcourt.testing import corpus_path, offline_project

with tempfile.TemporaryDirectory() as folder, offline_project(Path(folder)):
    with contextlib.redirect_stdout(io.StringIO()):
        assert main(["rank", str(corpus_path()), "--yes", "-q"]) == 0
    work = Path(folder) / ".ragcourt"
    results = json.loads(next(work.glob("runs/*/results.json")).read_text())
    lines = (work / "questions.jsonl").read_text().splitlines()[1:]
    questions = {item["id"]: item for item in map(json.loads, lines)}
    blame = results["blames"][0]
    question = questions[blame["question"]]
    print("question:", question["question"])
    print("gold:", question["document"], question["start"], question["end"], repr(question["quote"]))
    print("cause:", blame["mechanism"], "|", blame["level"])

assert question["quote"] == "Every running job has a timeout."
assert (question["category"], question["split"]) == ("paraphrase", "held-out")
assert [v["check"] for v in question["verdicts"]] == ["code rules", "valid", "answerable without documents"]
assert results["chosen"] == "fixed:size=60,overlap=0 | - | bm25 | none"
assert blame["mechanism"] == "retriever.keyword_only" and blame["level"] == "indicated"
assert "fake-embed finds it" in blame["evidence"]
```

## 1. The document

`timeouts.md` begins with the corpus's running header, then a heading and the sentence that will be the
gold quote:

```text
Larkspur Docs · version 3.2

# Timeouts

Every running job has a timeout. When a job runs longer than its timeout, Larkspur stops it and records
the attempt as failed.
```

## 2. The question

The header repeats across most documents, so it is never offered to the writer (design §6.1). The writer
was given the paragraph under `# Timeouts` for the `paraphrase` category and returned:

```text
question: Which statement covers the juliet matter, in other terms?
gold: timeouts.md 41 73 'Every running job has a timeout.'
```

The quote was found verbatim at characters 41 to 73. The checks, in order, each with its reason in the
question file:

```text
verdict: code rules -> pass                    (6 words, a sentence; shares no words with the quote)
verdict: valid -> pass                         (the judge)
verdict: answerable without documents -> pass  (the writer answered UNKNOWN; no judge call)
```

A hash of its id put it in the **held-out** split: it is used to report, never to choose.

## 3. The run

The search chose, on dev questions, `fixed:size=60,overlap=0 | - | bm25 | none`. On this question BM25
found no chunk holding the quote in its top 50:

```text
first hit: not in the top 50
```

## 4. The blame

```text
cause: retriever.keyword_only | indicated
evidence: BM25 does not retrieve the chunk; fake-embed finds it
fix: dense or hybrid retrieval; measured here and not finding it either: retriever dense, retriever hybrid
```

The question shares no word with its answer (it is a paraphrase), so a keyword retriever cannot find it.
The probes show an embedder does (with another chunker, in the first step), so the cause is the retriever's
method, not the vectors. The level is `indicated`: the dense and hybrid pipelines measured in this run, with
the same chunker, did not find it either, so no measurement confirms the fix.

`ragcourt explain --show ID` prints where the quote sits among the chunks:

```text
⟦59⟧Larkspur Docs · version 3.2

# Timeouts

«Every running job has a timeout.» When a job runs longer than its timeout, Larkspur stops it and records
the attempt as failed. The default timeout is 300 seconds, and a job can set its own when it is enqueued.

## How a job is⟧ ⟦60⟧stopped
```

The quote is whole inside chunk 59, so the chunker is not to blame; the retriever never returned that
chunk.
