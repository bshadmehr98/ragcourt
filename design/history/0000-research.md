# 0000: What exists already, and what is still to research (November 2026)

ragdoctor started on 2026-11-22 from the owner's brief ([0001-owner-brief.md](0001-owner-brief.md)). This
note records what was looked up before the first design was written. Each statement carries its evidence
level: `sourced` means it was read on a web page, a README, PyPI's JSON API or GitHub's API on 2026-11-22
(by a research agent working for the designer; the designer did not re-read every page); `inferred` means
it is our reasoning and has not been tested. Star counts and dates are as read that day.

## 1. The tools the brief names

**AutoRAG** (Marker-Inc-Korea; github.com/Marker-Inc-Korea/AutoRAG, PyPI `AutoRAG`).
- The repository now hosts "AutoRAG 2.0", a desktop agent; the RAG AutoML tool is "legacy" and in
  maintenance mode. Legacy PyPI 0.3.27 (2026-10-04), Apache-2.0, about 6.1k stars. `sourced`
- It searches node by node (retrieval, passage reranker, prompt maker, generator), passing "the best
  result from the previous node" to the next: a greedy search by stage, as the brief asks for. `sourced`
- Its ground truth `retrieval_gt` is tied to chunk ids ("if the chunk method is different, the
  retrieval_gt will be different, so we need to remap it"); chunking is part of data creation, not of the
  optimisation. `sourced`
- No confidence intervals and no per-question blame were found in its docs. `inferred` (absence)
- Gap: gold that does not depend on the chunker, so chunkers can be ranked fairly; intervals; blame; an
  audit with no model. `inferred`

**rag-forge** (ambiguous). No PyPI project of that name. The closest is github.com/hallengray/rag-forge
(MIT, 6 stars): a pipeline scaffolder with `audit` and `assess` commands scored against a "RAG Maturity
Model" with RAGAS, DeepEval and an LLM judge; PyPI `rag-forge-core` and `rag-forge-evaluator` 0.2.3
(2026-04-16). A second repository of the same name is a Streamlit comparison of four retrieval strategies
with an LLM judge. `sourced`. Its `audit` is judged by a model, not computed over chunks; it has no stage
leaderboard or code-computed blame. `inferred`

**chunk-bench** (github.com/obielin/chunk-bench, PyPI 1.0.0, 2026-04-12, 1 star). Ranks four built-in
chunkers on the user's text by recall, precision, MRR and F1 with no embeddings, using user-supplied
keyword lists as relevance. `sourced`. No embedders, retrievers, rerankers, intervals or blame. `inferred`

**chunkvet** (github.com/jay-tank/chunkvet, MIT, 0 stars, August 2026; its README says
`pip install chunkvet` but PyPI has no such project). An offline, model-free chunk auditor: oversized
(default 512 tokens), tiny, mid-unit splits (lowercase start, no terminal punctuation, unbalanced code
fence), size variance, zero overlap, near-duplicates by shingle Jaccard, with a CI exit code. Tokens are
estimated as characters / 4. `sourced`. It covers much of `audit`; missing are heading context, split
tables, repeated headers and footers, and the embedder's real tokenizer and limit. `inferred`

**MTCB** (Massive Text Chunking Benchmark; github.com/chonkie-inc/mtcb, now feyninc/mtcb; PyPI `mtcb`
0.1.0, 2026-02-07, Apache-2.0). A fixed benchmark (9 domains, about 17k questions over about 3k documents,
a 900-question "nano" set) reporting Recall@k, Precision@k and MRR@k for a chunker and embedder pair; a
`SimpleEvaluator` takes a custom corpus with `relevant_passages`, and a `DatasetGenerator` makes verified
questions from the user's documents. `sourced`. Whether generation needs an API key was not confirmed;
the examples use a hosted embedder. `inferred`. No rerankers, intervals or blame. `inferred`

**Chroma, "Evaluating Chunking Strategies"** (trychroma.com/research/evaluating-chunking, Smith and
Troynikov, 2024-07-03; code github.com/brandonstarxel/chunking_evaluation, MIT, about 500 stars, not on
PyPI). LLM-generated excerpts are kept as gold only if they match the corpus in full; chunkers are scored
by token-level IoU, precision, recall and precision-Ω, reported as mean ± standard deviation over 472
queries in five corpora; no rerankers. `sourced`. This is the origin of the brief's verbatim-quote gold
and token metrics; ragdoctor adds retrievers and rerankers, intervals instead of a standard deviation,
blame, an audit and a maintained command line. `inferred`

**Chonkie** (github.com/chonkie-inc/chonkie, now feyninc/chonkie; MIT, about 4.9k stars; PyPI 1.7.0,
2026-07-07). A chunking library whose own benchmarks measure speed and size, not retrieval quality.
`sourced`. A natural source of chunkers for a thin adapter. `inferred`

**Ragas** (github.com/explodinggradients/ragas, now vibrantlabsai/ragas; Apache-2.0, about 16k stars;
PyPI 0.4.4, 2026-11-14). LLM and non-LLM metrics and test-set generation; context recall in three forms
(LLM, string similarity to `reference_contexts`, id-based). `sourced`. It scores one pipeline; it does not
rank stage variants, attribute misses to a stage, or use span gold with intervals. `inferred`

## 2. Others found

- **ragblame** (github.com/pulkitnagpal/ragblame, Apache-2.0, 0 stars, created 2026-11-14, not on PyPI):
  "git blame for wrong RAG answers"; for each wrong answer it swaps one stage for a perfect version
  (re-chunk, exact search, passage first) across chunk, embed, index, rerank, pack and generate; a model
  writes questions with exact supporting quotes and judges every answer. `sourced`. **The closest prior
  art for both blame and quote gold.** It needs a model and a key for every run and diagnoses one
  pipeline rather than ranking variants with intervals. `inferred`
- **rag-doctor on PyPI** (1.0.0, 2026-03-09, MIT): "Agentic RAG pipeline failure diagnosis — no database,
  no LLM API, no cloud"; root causes such as retrieval miss, position bias, chunk fragmentation; a
  `ChunkOptimizer` that grid-searches chunk size; its repository links are unfilled placeholders.
  `sourced`. See §3 for the name.
- **thehalleyyoung/ragdoctor** (GitHub, Apache-2.0, 0 stars, 2026-05-13): `Doctor.diagnose()` (chunk-size
  outliers, boundary quality, near-duplicates, embedding collapse), an eight-axis `audit()` with
  `score_ci_95`, ranked repair "prescriptions". `sourced`
- **RAGChecker** (amazon-science; PyPI 0.1.9, 2024-09-25; about 1.1k stars): claim-level entailment
  diagnostics that split blame between retriever and generator; needs a model. `sourced`
- **RAGEC** (Layer 6, arXiv 2510.13975, EACL 2026; github.com/layer6ai-labs/rag-error-classification): a
  16-error taxonomy grouped by stage (chunking, retrieval, reranking, generation), classified by an LLM
  judge. `sourced`. The conceptual precedent for stage blame, decided by a model rather than code.
  `inferred`
- **Vectara open-rag-eval** (PyPI 0.3.0, 2025-12-15): TREC-RAG style metrics without golden chunks or
  answers; needs an OpenAI key. `sourced`
- **LlamaIndex `RetrieverEvaluator`**: MRR and hit rate against expected node ids; question generation
  needs a model. `sourced`. Its gold is tied to the chunker. `inferred`
- **RECTIFY** (arXiv 2609.16764, 2026-09-15): a workbench that groups failures into repair families and
  verifies repairs by rerunning in a sandbox. `sourced`
- **arXiv 2603.06976** (2026-03-07): 36 chunking methods × 5 embedders × 6 domains scored by nDCG@5 with
  LLM-graded relevance; no rerankers. `sourced`
- **BEIR, MTEB**: public benchmarks, active (metadata only was read). `sourced`. They do not run on the
  user's documents. `inferred`

## 3. The name (D-001)

- PyPI `ragdoctor`: free (404). `sourced`
- PyPI `rag-doctor` / `rag_doctor`: taken (§2), a RAG failure-diagnosis tool. pip normalises `ragdoctor`
  differently, so the upload is possible, but users would confuse the two. `sourced` / `inferred`
- GitHub: thehalleyyoung/ragdoctor (RAG diagnostics), hanhanwu/RagDoctor (archived, 9 stars, "traces
  failures back to root causes"), NeuroForgeLabs/rag-doctor (an npm CLI), and many unrelated medical
  chatbots. `sourced`
- Alternatives checked on PyPI only: `chunkdoctor` free (an unrelated Minecraft "ChunkDoctor" exists on
  GitHub); `ragblame` free on PyPI but a direct concept clash on GitHub; `retrievalscope` free on PyPI
  with no GitHub repositories. `sourced`
- **Second round (2026-11-22, after the owner asked for a name with "rag" that is used nowhere):** 60
  candidates checked by script against PyPI (both `ragx` and `rag-x`), npm and GitHub repository names
  (`gh api search/repositories "<name> in:name"`). Free on all three, with no repository whose name
  contains it: `ragsift`, `ragstethoscope`, `ragsplint`, `ragculprit`, `ragcalipers`, `ragcaliper`,
  `ragtally`, `ragprove`, `ragscout`, `ragsleuth`, `ragbisector`, `ragstage`, `ragstages`,
  `ragpinpoint`, `ragrootcause`, `ragseam`, `ragsplice`, `ragmeasure`, `ragreceipt`, `ragsurgeon`,
  `ragbiopsy`, `ragcensus`. `sourced`. A web search for the exact names `ragsift`, `ragculprit`,
  `ragsleuth`, `ragcaliper`, `ragpinpoint`, `ragbisector`, `ragscout`, `ragstage`, `ragtally`,
  `ragbiopsy`, `ragprove` and `ragseam` found no use of any of them; near names exist (RAGSwift, a
  self-hosted embeddings platform, next to `ragsift`; RAGXRay on PyPI; Ragnosis on Product Hunt).
  `sourced`. Taken or crowded: `ragtrace`, `ragbench`, `raglens`, `ragscope`, `ragprobe`, `ragrank`,
  `ragdiag`, `ragkit`, `ragxray` (on PyPI or as GitHub repository names), and `ragmedic` (20 repositories),
  `ragtune` (10). `sourced`. Domains and trademarks were not checked.
- Conclusion: "ragdoctor" is crowded by three RAG-diagnosis projects of nearly the same name. Raised as
  [D-001](../decisions.md#d-001-the-name-ragdoctor). `inferred`

## 4. What the survey changes in the design

- No tool found combines chunk-independent quote gold, all four stages, intervals and code-computed blame
  with no API key for the audit. The design keeps all four; ragblame and Chroma's report are cited as
  precedent. `inferred`
- chunkvet's checks and thresholds are a useful starting point for `audit` (design §5.1); ragdoctor adds
  heading context, split tables, repeated boilerplate and the real tokenizer. `inferred`
- AutoRAG confirms greedy search by stage is a workable shape; its remapping problem confirms why gold
  must not be chunk ids. `inferred`

## 5. What was not researched

- The READMEs of ARES, DeepEval, Haystack's evaluation, BEIR and MTEB (metadata only for the last two).
- AutoRAG's passage-reranker and token-metric pages; whether MTCB's generator needs a key.
- RECTIFY's code; arXiv 2603.06976's code and gold; an "arXiv 2609.31660" that appeared in a search and
  could not be verified.
- **How well small local models write questions with verbatim quotes**, and how many are dropped: first
  measured on the owner's machine in [0002-local-models.md](0002-local-models.md).
- How often the blame rules' boundaries (top 50, k) match what developers mean by "the retriever's
  fault"; no user has been asked.
- Which tokenizers can be loaded offline for common embedding models, and their install size (D-008);
  for Ollama models, [0002-local-models.md](0002-local-models.md) found that Ollama reports token counts.
- Whether a bootstrap over a few dozen held-out questions gives intervals narrow enough to separate
  anything on typical corpora; this will be measured on the bundled corpus and real-model tests (D-011).

## Sources

- https://alternativeto.net/software/ragswift/about ; https://pypi.org/project/ragxray/ ;
  https://www.producthunt.com/products/ragnosis/reviews

- https://github.com/Marker-Inc-Korea/AutoRAG ; https://pypi.org/pypi/AutoRAG/json ;
  https://autorag-docs.nomadamas.org/legacy/optimization/optimization.html
- https://github.com/hallengray/rag-forge ; https://github.com/Sakshamm-Thakurr/rag-forge
- https://github.com/obielin/chunk-bench ; https://pypi.org/pypi/chunk-bench/json
- https://github.com/jay-tank/chunkvet
- https://github.com/chonkie-inc/mtcb ; https://pypi.org/pypi/mtcb/json
- https://www.trychroma.com/research/evaluating-chunking ; https://github.com/brandonstarxel/chunking_evaluation
- https://github.com/chonkie-inc/chonkie ; https://pypi.org/pypi/chonkie/json
- https://github.com/explodinggradients/ragas ; https://docs.ragas.io (context recall)
- https://github.com/pulkitnagpal/ragblame
- https://pypi.org/project/rag-doctor/ ; https://github.com/thehalleyyoung/ragdoctor ;
  https://github.com/hanhanwu/RagDoctor ; https://github.com/NeuroForgeLabs/rag-doctor
- https://github.com/amazon-science/RAGChecker ; https://github.com/vectara/open-rag-eval
- https://arxiv.org/abs/2510.13975 ; https://github.com/layer6ai-labs/rag-error-classification
- https://arxiv.org/abs/2609.16764 ; https://arxiv.org/abs/2603.06976
- https://github.com/beir-cellar/beir ; https://github.com/embeddings-benchmark/mteb
