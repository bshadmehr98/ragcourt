# The audit

`ragcourt audit FOLDER` cuts your documents with each chunker and checks every chunk by code. No chat
model is called. Sizes are counted in the embedder's own tokens when it answers (labelled **measured**;
through Ollama, each chunk's count is the one Ollama reports); otherwise characters / 4 (labelled
**estimated**, everywhere). With no `--chunker`, the four native chunkers and your own are audited.

| Check | Flags a chunk that… | Near miss (not flagged) | What to do |
|---|---|---|---|
| `cut.mid_sentence` | ends where the source goes on with the same sentence | a sentence that ends in an abbreviation (`etc.`); the end of a paragraph or list item | a sentence-aware chunker, or a size that fits your paragraphs |
| `context.no_heading` | lies under a heading it does not contain | a chunk that repeats its heading | `markdown`, or a chunker that keeps headings |
| `split.table` | holds part, not all, of a table's rows | a table kept whole | a larger size, or a structure-aware chunker |
| `split.code` | holds part, not all, of a fenced or indented code block | a code block kept whole | the same |
| `boilerplate.repeated` | is mostly lines repeated across 30% of documents (headers, menus) | a line that repeats in one document | strip the boilerplate before chunking |
| `duplicate.near` | has 5-gram Jaccard ≥ 0.9 with an earlier chunk | similar but different text | remove duplicates; they crowd out answers |
| `size.tiny` | has fewer than 20 tokens | — | merge small pieces |
| `size.over_limit` | is longer than the embedder reads: the end is cut silently | — | a smaller size, or an embedder with a longer limit |

The thresholds are settings (`[audit]` in `ragcourt.toml`).

A measured count can never pass the limit: Ollama reports how much it read. A chunk whose count reaches
the limit was cut, and is flagged. The limit itself is measured too: Ollama reads less than a model
advertises unless told otherwise (bge-m3 advertises 8,192 tokens and reads 2,048 by default), so ragcourt
asks for the full context and measures what is read, once per model.

`--show DOC` prints the document with the boundaries marked: `⟦12⟧` where chunk 12 starts, `⟧` where a
chunk ends, `⟦12 cut.mid_sentence⟧` when a check flagged it. `--json` gives the same as data.

```python
import socket
import tempfile
from pathlib import Path

from ragcourt.cli import main
from ragcourt.testing import corpus_path

socket.socket.connect = lambda self, address: (_ for _ in ()).throw(ConnectionRefusedError())  # offline
with tempfile.TemporaryDirectory() as folder:
    code = main(
        ["audit", str(corpus_path()), "--chunker", "fixed:size=40,overlap=0", "--workdir", folder, "-q"]
    )
assert code == 0
```
