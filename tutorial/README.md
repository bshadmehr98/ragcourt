# The ragcourt tutorial

Learn RAG retrieval and ragcourt together, from zero. Each chapter explains one idea in plain words, shows
how ragcourt measures it, and gives you the command to try. No earlier knowledge of RAG is assumed.

## Where to start

- **New to RAG?** Read in order, from chapter 1.
- **Know RAG, want to use ragcourt?** Chapters 2, 10, 12 and 11.
- **Want to plug in your own code?** Chapter 16.

## Chapters

**Part 1. The basics**

1. [What RAG is, and why retrieval fails](01-what-is-rag.md)
2. [Install and a first run](02-install-and-first-run.md)

**Part 2. The four stages of a retrieval pipeline**

3. [Chunking: cutting documents into pieces](03-chunking.md)
4. [The audit: checking how chunks were cut](04-audit.md)
5. [Embeddings: turning text into numbers](05-embeddings.md)
6. [Retrieval: finding the right chunks](06-retrieval.md)
7. [Reranking: putting the best chunks first](07-reranking.md)

**Part 3. Measuring**

8. [Test questions and gold answers](08-test-questions.md)
9. [The judge](09-the-judge.md)
10. [The metrics, one by one](10-metrics.md)
11. [Intervals, ties and "too few to rank"](11-statistics.md)
12. [Ranking pipelines: the search and the leaderboards](12-ranking.md)
13. [Why a question was missed](13-why-questions-fail.md)

**Part 4. Using ragcourt day to day**

14. [Every command](14-commands.md)
15. [Settings and models](15-settings-and-models.md)
16. [Your own chunker, embedder, retriever or reranker](16-your-own-stages.md)
17. [Doctor: letting a model suggest a chunker](17-doctor.md)
18. [Files, privacy and safety](18-files-and-privacy.md)

**Part 5. In practice**

19. [Real runs: what we tested and what we saw](19-real-runs.md)
20. [Troubleshooting](20-troubleshooting.md)
21. [Glossary](21-glossary.md)

Every Python example in these chapters is run by ragcourt's tests, so what you read is what the code does.
