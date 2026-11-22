# Models

Every model has a **role**:

| Role | Does | Is shown |
|---|---|---|
| `writer` | writes questions and copies a quote that answers each | one passage of your documents at a time |
| `judge` | checks questions (see [judge.md](judge.md)) | a question, its quote, an answer |
| `embedders` | the embedding models ranked against each other | your chunks and questions |
| `reranker` | the chat model of the `llm` reranker | a question and up to 20 chunks |
| `doctor` | describes your documents, suggests (or writes) a chunker | samples of your documents |

**Defaults**, chosen by measurement on an 8 GB GPU (design/history/0002): `gemma4` as writer, judge,
reranker and doctor (19 of 20 quotes verbatim, 98% on the judge's self-test); `nomic-embed-text`,
`embeddinggemma` and `mxbai-embed-large` as embedders.

**Setup.** `ragcourt setup` checks that Ollama answers, reads your RAM (and GPU memory from `nvidia-smi`),
recommends models that fit, shows their sizes, pulls the missing ones only after your yes (or `--yes`),
writes a commented `ragcourt.toml`, and runs the judge's self-test.

**Changing one.** `ragcourt models` shows each role, its model, where the choice came from (built-in
default, `ragcourt.toml`, or a flag), whether it is installed and its size, and the judge's self-test.
`ragcourt models set judge qwen3:4b` writes `ragcourt.toml` keeping its comments and self-tests the new
judge at once; `ragcourt models set embedders nomic-embed-text,bge-m3` sets a list. For one run:
`--writer`, `--judge`, `--embedders`. Precedence: a flag, then `ragcourt.toml`, then the default; the plan
of every run prints which applied.

```python
import tempfile
from pathlib import Path

from ragcourt.cli import main
from ragcourt.testing import offline_project

with tempfile.TemporaryDirectory() as folder, offline_project(Path(folder)) as server:
    server.models["another-judge"] = 4096
    assert main(["models", "set", "judge", "another-judge", "-q"]) == 0
    assert 'judge = "another-judge"' in (Path(folder) / "ragcourt.toml").read_text()
```

**Endpoints.** Any OpenAI-compatible server (a hosted API, llama.cpp, vLLM, LM Studio) works once named:

```text
[endpoints.openai]
base_url = "https://api.openai.com/v1"
api_key_env = "OPENAI_API_KEY"

[models]
embedders = ["nomic-embed-text", "endpoint:openai/text-embedding-3-small"]

[prices]
"endpoint:openai/text-embedding-3-small" = 0.02   # dollars per million tokens
```

The key is read from the environment variable, sent only in a header, never written to any file. An
endpoint's price unknown is reported as unknown, never as zero; local models cost nothing.

**Embedders and their limits.** Each Ollama text is embedded in its own call, so its token count is the
one Ollama reports. Ollama reads less than a model advertises unless asked (`bge-m3` advertises 8,192
tokens and reads 2,048 by default), so ragcourt asks for the full context length and measures the limit in
force once per model (kept in `.ragcourt/cache/limits.json`). Questions and chunks get each model's
documented prefixes (`search_query:` and `search_document:` for nomic, for example); set
`ollama:model=nomic-embed-text,query_prefix=,document_prefix=` to turn them off and measure the
difference.

**Rerankers.** Ollama has no rerank route: the `llm` reranker asks the reranker role's chat model to order
the top 20 in one call. The `endpoint` reranker uses a `/rerank` route (vLLM, llama.cpp, TEI, Jina,
Cohere): `--rerankers "endpoint:model=endpoint:local/bge-reranker"`. The `cross-encoder` reranker and the
`st` embedder run sentence-transformers in-process (`pip install 'ragcourt[local]'`).
