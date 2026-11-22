# 7. Reranking: putting the best chunks first

A retriever is fast but rough. A **reranker** looks at the retrieved candidates more carefully, one
question at a time, and re-orders them. It cannot find what the retriever missed; it can only lift a chunk
from rank 12 into the top 5, or push one out.

| Reranker | How it works | Needs |
|---|---|---|
| `none` | keeps the retriever's order | — |
| `llm` | a chat model (the `reranker` role, `gemma4` by default) reads the question and the top 20 chunks and returns them in order, in one call | a local chat model |
| `endpoint` | a `/rerank` route (vLLM, llama.cpp, TEI, Jina, Cohere): `endpoint:model=endpoint:NAME/MODEL` | a configured endpoint |
| `cross-encoder` | a sentence-transformers cross-encoder, in-process | `pip install 'ragcourt[local]'` |
| your own | any function scoring candidates | chapter 16 |

Ollama has no rerank route, which is why the local default is the `llm` reranker.

The last step of ragcourt's search compares "no reranker" with each candidate reranker on the best pipeline
so far (chapter 12). A reranker costs one model call per question; it is worth it only when the numbers
say so. In our Kubernetes run the `llm` reranker raised the score from 0.70 to 0.80, the only step there
with a clear winner (chapter 19).

When the reranker's reply cannot be read, the retriever's order is kept.

Next: [test questions](08-test-questions.md).
