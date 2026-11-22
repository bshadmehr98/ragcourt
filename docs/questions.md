# Questions and gold quotes

Every question comes with a **gold quote**: an exact span of one of your documents that answers it. The
quote is found in the source by code (exactly, then with whitespace runs treated as equal); a quote that is
not found drops its question. Gold therefore never depends on a chunker, and every chunker is judged on
the same questions.

## Categories

One mixed set cannot say which embedder is good at what, so questions are written by category, each aimed
at a known weakness of retrieval. Passages that can serve a category are chosen by code, and membership is
checked, not assumed:

| Category | Tests | Passages offered | Checked by |
|---|---|---|---|
| `paraphrase` | the same meaning in different words | any | code: few words shared with the quote |
| `keyword` | a few search terms | any | code: 2 to 6 words, no question mark |
| `exact_term` | a rare identifier, name or number with its unit | holding a term found in one document only | code: the term is in the question and the quote |
| `distractor` | worded like a similar passage that does not answer it | pairs of similar passages from different documents | code: uses two of the other passage's own words; judge: the other passage does not answer it |
| `negation` | what is not done, the exception | holding a negation | code: a negation in question and quote; judge |
| `numeric` | a number, default, limit, version or date | holding a number in prose | code: the quote holds a number; judge: it is the asked value |
| `user` | your own questions | — | the quote is found |

Headers and footers repeated across documents are never offered. A category your corpus cannot support
(no rare terms, no similar passages) gets fewer questions; one with fewer than 30 held-out questions is
reported as **too few to rank** and left out of the overall score.

## How many

90 per category by default (`[questions] per_category`): 30 to choose pipelines (**dev**), 60 to report
on (**held-out**), split by a hash of each question and the seed, a third per category. About 540
questions took 44 minutes for 160 pages of documentation on an 8 GB GPU, once per corpus; they are written as they come, reused while
your documents and settings do not change, and resumed after an interruption.

## Filters

In order, each drop counted by reason: not verbatim; the code rules (a quote of at least 6 words, a
sentence, at most 120 tokens; a question of at least 3 words outside `keyword`); not of its category;
a duplicate; not valid (judge); answerable without the documents (the writer answers without them; an
`UNKNOWN` keeps the question with no judge call; an answer the judge grades correct drops it).

`ragcourt questions show --dropped --reason "not valid"` lists the drops with the judge's reasons.

## Your own questions

```text
ragcourt questions docs/ --questions-file mine.jsonl
```

One JSON object per line: `question`, `quote`, and optionally `document` and `start`. The quote must be
found; a quote found in more than one document needs `document`, and one found twice in a document needs
`start` (its character offset there); a question without a quote is rejected (it cannot be scored). Your
questions are never dropped by the judge. With `--questions 0` (or `categories = []`) only your questions
are used, and no writer or judge is called.

```python
import json
import tempfile
from pathlib import Path

from ragcourt.cli import main
from ragcourt.testing import corpus_path, offline_project

with tempfile.TemporaryDirectory() as folder, offline_project(Path(folder)):
    mine = Path(folder) / "mine.jsonl"
    mine.write_text(
        json.dumps(
            {"question": "Is the dashboard public?", "quote": "The dashboard has no login of its own."}
        )
        + "\n"
    )
    assert main(["questions", str(corpus_path()), "--questions-file", str(mine), "-q"]) == 0
    kept = [
        json.loads(line)
        for line in (Path(folder) / ".ragcourt" / "questions.jsonl").read_text().splitlines()[1:]
    ]
    assert [q["document"] for q in kept if q["category"] == "user"] == ["security.md"]
```
