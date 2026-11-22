# 6. Retrieval: finding the right chunks

The **retriever** takes the question and returns the chunks most likely to answer it, best first. ragcourt
takes the top 50 (the **depth**); the top 5 (**k**) are what a language model would read.

## The three built-in retrievers

**`dense`: search by meaning.** The question's vector is compared with every chunk's vector by cosine
similarity. Finds answers worded differently from the question ("How long until a job is tried again?"
finds "The first retry waits 10 seconds"). Can miss exact names and numbers.

**`bm25`: search by words.** The classic keyword search (Okapi BM25): chunks score higher when they share
the question's words, especially rare ones, and lower when they are long. Needs no embedder. Finds exact
terms like `max_inflight` reliably; misses answers that use other words. A chunk that shares no word with
the question is not returned at all.

**`hybrid`: both.** Runs dense and BM25 and merges the two lists by **reciprocal-rank fusion**: each chunk
scores `1 / (60 + its rank)` in each list, and the scores add up. A chunk near the top of either list
rises. Parameters: `k` (60), `dense_weight` and `bm25_weight` (1 each).

```python
from ragcourt import stages
from ragcourt.testing import FakeEmbedder

stages.load_builtins()
chunks = [
    "Set max_inflight to limit open jobs.",
    "The worker retries failed jobs later.",
    "Dashboards show queue age.",
]
embedder = FakeEmbedder()
vectors = embedder.embed(chunks).vectors


def embed_query(text: str) -> list[float]:
    return embedder.embed([text], as_query=True).vectors[0]


bm25 = stages.find("retriever", "bm25").function(chunks, vectors, embed_query)
hybrid = stages.find("retriever", "hybrid").function(chunks, vectors, embed_query)
assert bm25("what does max_inflight do", 3)[0][0] == 0  # the exact word decides
assert bm25("unrelated words", 3) == []  # no shared word: nothing retrieved
assert hybrid("what does max_inflight do", 3)[0][0] == 0
```

## Which one wins?

It depends on your questions. ragcourt's question kinds (chapter 8) are made to show it: `exact_term` and
`keyword` questions favour BM25, `paraphrase` questions favour dense, and hybrid often does well on both.
The leaderboard says so per kind ("On paraphrase, … dense leads"). In our Kubernetes run (chapter 19), BM25
beat dense overall but lost clearly on paraphrase questions.

Search here is exact: every chunk is compared, so nothing is lost to approximation. That is fine up to
about 200,000 chunks.

Next: [reranking](07-reranking.md).
