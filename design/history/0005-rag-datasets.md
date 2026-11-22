# 0005: Public datasets for testing ragcourt on real data (2026-11-22)

Which public RAG datasets suit ragcourt, whose gold answers are verbatim quotes (character spans) in whole
documents. Surveyed from dataset cards, papers and repositories on 2026-11-22. `sourced` means read at the
link; `measured` means downloaded and checked on the owner's machine (see
[0004](0004-real-data.md)); `inferred` means our reasoning. Licences were read from cards and repositories,
not checked by a lawyer.

## Best fits

| Dataset | Corpus | Questions | Gold | Licence | Fit |
|---|---|---|---|---|---|
| **Chroma chunking evaluation** ([report](https://research.trychroma.com/evaluating-chunking), [data](https://github.com/brandonstarxel/chunking_evaluation)) | 5 Markdown files, 1.44 M chars: State of the Union, WikiTexts, chat logs, finance, PubMed | 472 | `{content, start_index, end_index}` per excerpt; 790 of 790 exact in ragcourt's loaded text `measured` | repository MIT; source texts carry their own terms `sourced` | **Good.** ragcourt's gold format almost exactly; questions are model-written and easy (0004 §3) |
| **MultiHop-RAG** ([paper](https://arxiv.org/abs/2401.15391), HF `yixuantt/MultiHopRAG`) | 609 whole news articles, 6.8 MB | 2,556: comparison 856, inference 816, temporal 583, null (no answer) 301 `measured` | evidence sentences, 6,084 of 6,084 verbatim in the article text `measured`; offsets by search | ODC-BY `sourced` | **Good.** Whole documents, multi-hop and unanswerable questions; some questions lean on metadata (outlet, date) not in the text `inferred` |
| **LegalBench-RAG** ([paper](https://arxiv.org/abs/2408.10343), [repo](https://github.com/ZeroEntropy-AI/legalbenchrag)) | 714 contracts as `.txt`, about 80 M chars; a mini set of 72 documents and 776 questions | 6,858 (the paper also says 6,889) | `{file_path, span: [start, end]}` character spans `sourced` | repository MIT; underlying sets not checked `sourced` | **Good** for long, repetitive text and look-alike clauses; data on Dropbox, not on Hugging Face |
| **ConditionalQA** ([paper](https://arxiv.org/abs/2110.06884), [repo](https://github.com/haitian-sun/ConditionalQA)) | gov.uk pages as HTML elements | dev 285 | verbatim HTML elements as evidence `sourced` | CC BY-SA 4.0 on the site, a BSD-2 file in the repo `sourced` | **Good to partial.** Real HTML, yes/no, conditions, no-answer questions; licence unclear, so download at test time |
| **Qasper** (HF `allenai/qasper`) | 1,585 NLP papers as sections and paragraphs | 5,049 | evidence paragraphs and highlighted sentences, no offsets `sourced` | CC BY 4.0 `sourced` | **Partial to good** once papers are written out as Markdown and offsets found by search `inferred` |

## Partial or poor fits

| Dataset | Why not first |
|---|---|
| SQuAD 2.0 (CC BY-SA 4.0) | paragraphs; offsets point at short answers, not evidence; many unanswerable questions `sourced` |
| Natural Questions (CC BY-SA 3.0) | whole Wikipedia HTML with byte offsets, ideal format, but a 45 GB download `sourced` |
| RepliQA (CC BY 4.0) | fictional documents (no answering from memory); gold paragraph matched verbatim in about half of a 100-row sample `sourced` |
| FreshStack (CC BY-SA 4.0) | real Stack Overflow questions on software docs and code, but gold is chunk-level `sourced` |
| HotpotQA, ConcurrentQA, ClapNQ | short passages, not documents `sourced` |
| RAGBench (CC BY 4.0) | pre-chunked passages only `sourced` |
| FinanceBench, Open RAG Benchmark, CRAG | non-commercial licences (CC BY-NC 4.0); FinanceBench needs PDFs; CRAG has no evidence spans `sourced` |
| FRAMES, NarrativeQA, MS MARCO, BEIR / MTEB | links or passages, answers without evidence spans, or document-level relevance only `sourced` |
| TechQA (IBM) | registration required `sourced` |

No public question set over software documentation with character-span gold was found; the closest is
FreshStack. `sourced`

## How ragcourt should use them

1. **Chroma's set** first: its excerpts with offsets are user questions with quotes (design §6.3), so a
   converter to ragcourt's question file gives a real-data acceptance run with no model writing questions.
   Its questions are easy, so it checks the pipeline, not the hard categories. `inferred`
2. **MultiHop-RAG** next: whole articles, verbatim evidence and unanswerable questions; the first quote of
   each question as gold for single-quote scoring, the rest kept for the multi-hop limit of §18. `inferred`
3. **LegalBench-RAG mini** as a stress test of chunking long, repetitive documents and of `distractor`
   blame. `inferred`
4. None of these goes in the repository: they are downloaded by the real-data tests (`tests/real/`) into
   a cache, with their licence printed. Small vendored subsets would need attribution (ODC-BY) or
   share-alike (CC BY-SA); the non-commercial sets stay out. `inferred`
