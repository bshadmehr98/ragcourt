# 5. Embeddings: turning text into numbers

An **embedding model** turns a text into a **vector**: a list of a few hundred numbers. Texts with similar
meaning get vectors that point in similar directions. The question gets a vector too, and the retriever
looks for the chunks whose vectors are closest to it (chapter 6).

```python
from ragcourt.testing import FakeEmbedder

embedder = FakeEmbedder()  # a stand-in that runs anywhere; real models capture meaning far better
question, near, far = embedder.embed(
    [
        "how long do retries wait",
        "retries wait ten seconds before the next attempt",
        "the dashboard has no login",
    ],
    as_query=True,
).vectors


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


assert cosine(question, near) > cosine(question, far)
```

**Closeness** is measured by **cosine similarity**: 1 means the same direction, 0 unrelated.

## Models

ragcourt compares the embedders listed in `[models] embedders`. Any Ollama embedding model works: write
its name (`nomic-embed-text`, `bge-m3`, `qwen3-embedding:0.6b`). Models we measured on an 8 GB GPU:

| Model | Texts per second | Vector size | Input limit |
|---|---|---|---|
| `all-minilm` | 125 | 384 | 512 (Ollama reads 256 by default) |
| `nomic-embed-text` | 107 | 768 | 2,048 |
| `mxbai-embed-large` | 59 | 1,024 | 512 |
| `embeddinggemma` | 51 | 768 | 2,048 |
| `bge-m3` | 44 | 1,024 | 8,192 (Ollama reads 2,048 by default) |
| `qwen3-embedding:0.6b` | 8 | 1,024 | 32,768 |

Faster is not better: which one finds your answers is what `rank` measures.

## Three details that change results

**The input limit in force.** A model reads at most so many tokens and drops the rest without a warning.
Ollama reads *less* than some models advertise unless asked: we measured `bge-m3` reading 2,048 of its
8,192 tokens. ragcourt asks for the full length and measures the limit actually in force with one
over-long text, once per model (kept in `.ragcourt/cache/limits.json`).

**Prefixes.** Some models want a marker before questions and another before passages (`nomic-embed-text`:
`search_query:` and `search_document:`). ragcourt adds each model's documented prefixes. To compare
without them: `ollama:model=nomic-embed-text,query_prefix=,document_prefix=`. On the texts we tried, they
changed results by a few questions either way, which is why ragcourt lets you measure it.

**Token counts.** Each chunk is embedded in its own call, so the token count Ollama reports is that chunk's
own. This is what lets the audit measure sizes and flag chunks over the limit.

## The cache

Embedding is the slow part. Every vector is kept in `.ragcourt/cache/embeddings/` (plain files: a list of
text hashes and the vectors), so a second run with the same documents embeds nothing, and changing one
document embeds only its chunks. `ragcourt cache clear` deletes it.

## Other embedders

- **An endpoint**: any OpenAI-compatible server (a hosted API, vLLM, llama.cpp, LM Studio), named as
  `endpoint:NAME/MODEL` after you configure it (chapter 15). Token counts are estimated unless you give a
  tokenizer: `endpoint:model=endpoint:openai/text-embedding-3-small,tokenizer=tiktoken:cl100k_base` (needs
  `pip install 'ragcourt[tokens]'`).
- **sentence-transformers** in-process: the `st` embedder (`pip install 'ragcourt[local]'`, brings torch).
- **Your own** (chapter 16).

Next: [retrieval](06-retrieval.md).
