# Stages

A stage is one implementation of one of four kinds: a **chunker**, an **embedder**, a **retriever** or a
**reranker** (design §7). The built-in stages and the optional extras are listed here as they are built.

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
| embedder | `@embedder("name")` | `(**params) -> Embedder`: an object with `model`, `max_tokens`, `tokenizer` and `embed(texts, *, as_query=False)`, which returns `Embedded(vectors, token_counts)` (`ragcourt.types`) |
| retriever | `@retriever("name")` | `(chunks, vectors, embed_query, **params) -> search`, where `search(query, depth)` returns `(chunk index, score)` pairs, best first |
| reranker | `@reranker("name")` | `(query, candidates, **params) -> list[float]`: one score per candidate |

Parameters are keyword arguments with defaults, so they can be set by name later
(`by_paragraph:min_chars=400`); a name is letters, digits, `_`, `.` and `-`. Two stages of the same kind
with the same name are an error that names both places (file and line). Your stages are your own code and run in-process like any Python you write; code a model
wrote is handled differently (design §12).
