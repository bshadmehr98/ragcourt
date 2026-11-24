# 2. Install and a first run

## What you need

- Python 3.11 or newer.
- [Ollama](https://ollama.com), which runs language and embedding models on your own machine. ragcourt
  uses it by default; nothing is sent to the internet.

```text
pip install ragcourt
ragcourt setup
```

`setup` does this, once per machine:

1. Checks that Ollama answers. If not, it tells you how to start it.
2. Reads how much memory your machine has and recommends models that fit. On a machine with an 8 GB GPU:
   `gemma4` to write and judge questions, and `nomic-embed-text`, `embeddinggemma` and
   `mxbai-embed-large` as the embedders to compare.
3. Shows each model's download size and **asks before downloading** (`--yes` skips the question).
4. Writes `ragcourt.toml`, with one line per model and a comment saying what each does.
5. Tests the judge model on 40 known cases (chapter 9).

## Try everything without models first

ragcourt ships a small set of made-up documents (a fictional job queue called Larkspur) and fake models,
so you can see every output in seconds:

```python
import tempfile
from pathlib import Path

from ragcourt.cli import main
from ragcourt.testing import corpus_path, offline_project

with tempfile.TemporaryDirectory() as folder, offline_project(Path(folder)):
    assert main(["audit", str(corpus_path()), "--embedder", "fake", "-q"]) == 0
    assert main(["rank", str(corpus_path()), "--yes", "-q"]) == 0
    assert main(["explain", "-q"]) == 0
```

The [examples folder](../examples/README.md) has one such script per feature.

## Your first real run

```text
ragcourt audit my_docs/      # seconds: how the chunkers cut your text (chapter 4)
ragcourt rank my_docs/ --quick   # a quick look in minutes: where the misses are, no winner named
ragcourt rank my_docs/       # the ranking: plan and time estimate first (about an hour, chapter 12); reuses the quick look's questions
ragcourt explain             # why each missed question was missed (chapter 13)
ragcourt report              # the same results as one HTML page
```

`my_docs/` is a folder of `.md`, `.txt`, `.rst` or `.html` files. Subfolders are read too; hidden files
and folders are skipped. PDF is not supported yet: convert it to text first.

Next: [chunking](03-chunking.md).
