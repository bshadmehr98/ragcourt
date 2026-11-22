# 1. What RAG is, and why retrieval fails

**RAG** (retrieval-augmented generation) answers a question about *your* documents in two moves:

1. **Retrieve**: find the few passages of your documents that hold the answer.
2. **Generate**: give those passages to a language model, which writes the answer.

If step 1 brings back the wrong passages, step 2 cannot answer well, however good the model is. ragcourt is
about step 1: it measures how well your retrieval finds the right passages, and tells you why it fails.

## The retrieval pipeline

Retrieval is itself four stages, and each one can lose the answer:

```text
your documents
   │  1. chunker   cuts each document into pieces ("chunks")
   ▼
chunks
   │  2. embedder  turns every chunk (and later the question) into a vector of numbers
   ▼
vectors
   │  3. retriever finds the 50 chunks closest to the question
   ▼
50 candidates
   │  4. reranker  re-orders them, so the best few come first
   ▼
the top k chunks (k = 5 by default) go to the language model
```

A **pipeline** is one choice for each stage, for example *markdown chunker · nomic-embed-text embedder ·
dense retriever · no reranker*. There are many choices at every stage, and the best one depends on your
documents. Blog posts and public leaderboards were measured on someone else's text.

## How the answer gets lost

- The **chunker** cut the answer in half, or buried it in a long chunk about something else.
- The chunk is longer than the **embedder** can read, and the answer sits in the part it never read.
- The **embedder** does not see that the question and the answer mean the same thing, or blurs an exact
  name like `max_inflight`.
- The **retriever** searched by meaning when the question needed exact words, or the other way round.
- A passage that *looks* like the answer but is not took its place.
- The **reranker** pushed the right chunk out of the top k.

## What ragcourt does about it

1. It writes test questions about your documents, each with a **gold answer**: an exact quote from your
   text (chapter 8).
2. It runs many pipelines on those questions and measures how often each one returns the quote (chapters
   10 to 12).
3. It says which pipeline is best, and whether "best" is real or just luck (chapter 11).
4. For every question the best pipeline still misses, it says which stage lost it and why (chapter 13).

Everything runs with local models on your machine by default. Next: [install it](02-install-and-first-run.md).
