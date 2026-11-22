# 21. Glossary

| Word | Meaning | Chapter |
|---|---|---|
| **audit** | checks of how chunks were cut, by code | 4 |
| **BM25** | keyword search scoring shared words, rare words more | 6 |
| **blame / cause** | the stage and mechanism that lost a missed question | 13 |
| **bootstrap** | redrawing the questions at random, with replacement, to see how much a score could vary | 11 |
| **ceiling** | the share of questions still answerable after a stage | 13 |
| **chunk** | a piece of a document, the unit a retriever returns | 3 |
| **chunker** | the stage that cuts documents into chunks | 3 |
| **confirmed / indicated** | a cause backed by a measured alternative / by the probes only | 13 |
| **cosine similarity** | how close two vectors point, 1 = same direction | 5 |
| **dense retrieval** | search by the embedder's vectors (meaning) | 6 |
| **depth** | how many chunks the retriever returns (50) | 6 |
| **dev / held-out** | questions used to choose (one third) / to report (two thirds) | 11 |
| **distractor** | a question worded like a look-alike passage that does not answer it | 8 |
| **embedder / embedding** | a model turning text into a vector / that vector | 5 |
| **endpoint** | a model server other than Ollama (OpenAI-compatible) | 15 |
| **gold quote** | the exact text from your document that answers a question | 8 |
| **hit** | a chunk that holds the whole gold quote | 10 |
| **hybrid** | dense and BM25 merged by reciprocal-rank fusion | 6 |
| **input limit** | the most tokens an embedder reads; the rest is ignored | 5 |
| **interval** | the range a score would likely fall in with other questions (95%) | 11 |
| **judge** | the model that filters questions, after passing its self-test | 9 |
| **k** | how many chunks a language model reads (5) | 10 |
| **leaderboard** | one search step's pipelines, ranked, with intervals | 12 |
| **metric** | a number from 0 to 1 scoring one retrieval | 10 |
| **overlap** | tokens a chunk repeats from the previous one | 3 |
| **paired difference** | the difference of two pipelines on the same questions; decides ties | 11 |
| **pipeline** | one chunker, embedder, retriever and reranker together | 1 |
| **probe** | an extra measurement made to tell causes apart | 13 |
| **RAG** | retrieval-augmented generation: find passages, then let a model answer from them | 1 |
| **reference tokens** | words and punctuation, counted the same for every model | 3 |
| **reranker** | the stage that re-orders retrieved chunks | 7 |
| **retriever** | the stage that finds candidate chunks for a question | 6 |
| **role** | a job a model does: writer, judge, embedders, reranker, doctor | 15 |
| **spec** | a stage and its parameters: `recursive:size=256,overlap=32` | 3 |
| **span** | a start and end position in a document | 8 |
| **stage** | one of the four parts of a pipeline | 1 |
| **token** | roughly a word or punctuation mark; models count their own | 3 |
| **too few to rank** | a kind with too few held-out questions to score fairly | 11 |
| **vector** | a list of numbers representing a text's meaning | 5 |
| **writer** | the model that writes questions | 8 |

Back to [the start](README.md).
