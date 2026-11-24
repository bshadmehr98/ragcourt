# Stages

A stage is one implementation of one of four kinds: a **chunker**, an **embedder**, a **retriever** or a
**reranker** (design §7). Each is named, and its parameters are given after a colon:
`recursive:size=256,overlap=32`. A misspelled parameter is an error that lists the right ones.

## Built-in

| Kind | Name | Needs |
|---|---|---|
| chunker | `fixed` (windows of reference tokens, with overlap) | — |
| chunker | `recursive` (paragraphs, sentences, lines, words, packed up to a size) | — |
| chunker | `sentence` (whole sentences packed up to a size) | — |
| chunker | `markdown` (one section per heading, heading kept, then `recursive` inside) | — |
| chunker | `chonkie.token`, `chonkie.sentence`, `chonkie.recursive` | `pip install 'ragcourt[chonkie]'` |
| chunker | `langchain.recursive`, `langchain.markdown` | `pip install 'ragcourt[langchain]'` |
| embedder | `ollama` (any Ollama embedding model: write its name, e.g. `nomic-embed-text`) | Ollama |
| embedder | `endpoint` (any `/embeddings`: `endpoint:NAME/MODEL`; `tokenizer=tiktoken:cl100k_base` counts exactly) | an endpoint (`[tokens]` for counts) |
| embedder | `st` (sentence-transformers, in-process) | `pip install 'ragcourt[local]'` |
| retriever | `dense` (cosine, exact, in memory) | an embedder |
| retriever | `bm25` (pure Python) | — |
| retriever | `hybrid` (reciprocal-rank fusion of `dense` and `bm25`; `k`, `dense_weight`, `bm25_weight`) | an embedder |
| reranker | `none`, `llm` (a chat model orders the top 20), `endpoint` (a `/rerank` route) | a model for the last two |
| reranker | `cross-encoder` (in-process) | `pip install 'ragcourt[local]'` |

Chunk sizes of the native chunkers are in reference tokens (words and punctuation); the audit reports
sizes in your embedder's own tokens.

## Your own stage, in one file

Put a Python file in a folder named `ragcourt_stages/` in your project (or name another folder with
`stages_dir` in `ragcourt.toml`). Every `.py` file in it is imported in sorted order (hidden files are
left out), and each function you decorate becomes a stage under the name you give it. A file can import
another one in the folder, for shared helpers: `from ragcourt_stages.helpers import paragraphs`.

```python
from ragcourt.stages import chunker, find


@chunker("by_paragraph")
def by_paragraph(text: str, min_chars: int = 200) -> list[str]:
    """One chunk per paragraph, skipping paragraphs shorter than min_chars."""
    return [part for part in text.split("\n\n") if len(part) >= min_chars]


assert find("chunker", "by_paragraph").function is by_paragraph
```

What each kind receives and returns:

| Kind | Decorator | Your function |
|---|---|---|
| chunker | `@chunker("name")` | `(text, **params) -> list[str]`; every string must be found in the text, ragcourt finds where |
| embedder | `@embedder("name")` | `(**params) -> Embedder`: an object with `model`, `max_tokens`, `tokenizer` and `embed(texts, *, as_query=False)`, which returns `Embedded(vectors, token_counts)` (`ragcourt.types`); take a `client` parameter to be given the model client |
| retriever | `@retriever("name")` | `(chunks, vectors, embed_query, **params) -> search`, where `search(query, depth)` returns `(chunk index, score)` pairs, best first |
| reranker | `@reranker("name")` | `(query, candidates, **params) -> list[float]`: one score per candidate |

Parameters are keyword arguments with defaults, so they can be set by name (`by_paragraph:min_chars=400`);
a name is letters, digits, `_`, `.` and `-`. Two stages of the same kind with the same name are an error
that names both places (file and line). Your stages are your own code and run in-process like any Python
you write, on every command run from that folder (so don't run ragcourt inside a folder you downloaded); code a model wrote is handled differently (design §12).

## Your own pipeline: measure the system you already have

The four kinds above are stages ragcourt runs. If you already have a retrieval system (a vector database, a
framework's retriever, an index you built months ago), you do not rebuild it from them: you give ragcourt
one function that asks it.

```python
from ragcourt.stages import find, pipeline, pipeline_chunks

MY_INDEX = ["Jobs are retried three times.", "A dead job is kept for 14 days."]  # stands for your database


@pipeline("mine")
def mine(query: str, depth: int) -> list[str]:
    """Your system's chunk texts for one question, best first."""
    words = set(query.lower().split())
    return sorted(MY_INDEX, key=lambda chunk: -len(words & set(chunk.lower().split())))[:depth]


@pipeline_chunks("mine")  # optional: every chunk your system holds
def mine_chunks() -> list[str]:
    return MY_INDEX


assert find("pipeline", "mine").function("how long is a dead job kept", 1) == [MY_INDEX[1]]
```

```text
ragcourt rank DOCS --pipeline mine              # the search, then yours beside the best it found
ragcourt rank DOCS --pipeline mine --no-search  # only yours: no embedding model is needed
ragcourt explain                                # why each question your system missed was missed
```

- ragcourt finds where each returned text lies in your documents, then scores your system on the same
  held-out questions, with the same metrics and intervals as any pipeline. The run is about your system:
  `explain` and the report show **its** misses.
- A text that is **not text of your documents** (your system rewrote it, or added a title or a summary), or
  that is found in more than one place, cannot be scored as an answer: it keeps its rank and holds no quote,
  while its words still count against token precision and the token budget; how many there are is said
  under the board. If no text at all is found, the run stops and says so.
- Blame is coarser than for ragcourt's own pipelines, because ragcourt cannot look inside your system:
  `retrieval.not_found` (a chunk holds the quote and your system does not return it in the top 50) instead
  of an embedder or retriever mechanism, and the `ranking` mechanisms when it is returned below k. With
  `@pipeline_chunks`, a quote that no chunk holds whole is the `chunker`'s; without it, such a miss is
  `retrieval.not_found` with a note.
- A miss is `confirmed` when a pipeline ragcourt measured in the same run finds the question, and the fix
  names it. That shows the question can be found, not which stage of your system lost it.
- Without `@pipeline_chunks`, nDCG is measured against a chunk that holds the whole quote.
- Your function runs in-process like any stage of yours. The question's text goes wherever your code sends
  it; the plan says so before it is called. Nothing in your system is chosen or tuned.
