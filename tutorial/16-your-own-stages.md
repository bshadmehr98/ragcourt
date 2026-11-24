# 16. Your own chunker, embedder, retriever or reranker

Your own code is measured exactly like the built-ins: same questions, same leaderboards, same blame. A
stage is one decorated Python function in a file in `ragcourt_stages/` (or the folder named by
`stages_dir`). Every `.py` file there is imported, in sorted order.

## A chunker

```python
from ragcourt.stages import chunker, find


@chunker("by_paragraph")
def by_paragraph(text: str, min_chars: int = 200) -> list[str]:
    """One chunk per paragraph, skipping paragraphs shorter than min_chars."""
    return [part for part in text.split("\n\n") if len(part) >= min_chars]


assert find("chunker", "by_paragraph").function is by_paragraph
```

Then:

```text
ragcourt audit my_docs/ --chunker "by_paragraph:min_chars=400"
ragcourt rank my_docs/ --chunkers "by_paragraph;by_paragraph:min_chars=400;markdown"
```

Parameters are keyword arguments with defaults, set by name in the spec. A wrong name lists the right
ones. Every chunk must be text found in the document (chapter 3); ragcourt finds where.

## The other kinds

| Kind | Decorator | Your function |
|---|---|---|
| chunker | `@chunker("name")` | `(text, **params) -> list[str]` |
| embedder | `@embedder("name")` | `(**params) -> Embedder`: an object with `model`, `max_tokens`, `tokenizer` and `embed(texts, *, as_query=False)` returning `Embedded(vectors, token_counts)`; add a `client` parameter to be given ragcourt's model client |
| retriever | `@retriever("name")` | `(chunks, vectors, embed_query, **params) -> search`, where `search(query, depth)` returns `(chunk index, score)` pairs, best first |
| reranker | `@reranker("name")` | `(query, candidates, **params) -> list[float]`: one score per candidate, higher is better |

A retriever that, say, boosts chunks from the document whose title matches the question:

```python
from collections.abc import Callable

from ragcourt.stages import retriever


@retriever("title_boost")
def title_boost(
    chunks: list[str],
    vectors: list[list[float]],
    embed_query: Callable[[str], list[float]],
    boost: float = 0.2,
):
    def search(query: str, depth: int) -> list[tuple[int, float]]:
        q = embed_query(query)
        words = set(query.lower().split())
        scores = []
        for index, vector in enumerate(vectors):
            score = sum(a * b for a, b in zip(q, vector))
            first_line = chunks[index].split("\n", 1)[0].lower()
            scores.append((index, score + (boost if words & set(first_line.split()) else 0.0)))
        return sorted(scores, key=lambda pair: -pair[1])[:depth]

    return search
```

## The system you already have

If you already run a retrieval system, wrap it in one function instead of rebuilding it: a question in,
your chunk texts out, best first.

```text
# ragcourt_stages/mine.py
from ragcourt.stages import pipeline

@pipeline("mine")
def mine(query: str, depth: int) -> list[str]:
    return [hit.text for hit in my_index.search(query, limit=depth)]
```

```text
ragcourt rank my_docs/ --pipeline mine --no-search    # only your system: no embedding model needed
ragcourt rank my_docs/ --pipeline mine                # and compare it with the best ragcourt finds
```

ragcourt scores it on the same questions and explains its misses. It cannot look inside your system, so
a chunk it does not return is `retrieval.not_found`, not an embedder or a retriever cause; list your
chunks with `@pipeline_chunks` and a quote cut in two is traced to your chunker. Chunks that are not text
of your documents (a title or summary added) cannot be scored and are counted. The details are in
[the stages page](../docs/stages.md).

## Rules

- A name is letters, digits, `_`, `.` and `-`. Two stages of one kind with the same name is an error naming
  both files and lines.
- A file can import a helper from the same folder: `from ragcourt_stages.helpers import paragraphs`.
- Your stages run in-process like any Python you write. Code a *model* wrote is treated differently
  (chapter 17).
- `ragcourt audit` lists your chunkers with the built-ins, so you can check how they cut before ranking.

Next: [doctor](17-doctor.md).
