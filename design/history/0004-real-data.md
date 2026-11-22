# 0004: Step 1 on real data, and what Ollama's embedding API really does (2026-11-22)

After step 1 (foundations) was merged, the owner asked for it to be tried on real data with real models,
for the tests to be checked, and for what is wrong to be found. This note records what was run and what
it showed. `measured` means run on the owner's machine today with the scripts beside this note;
`inferred` means our reasoning. The machine is the one of [0002](0002-local-models.md); every model
needed was already installed, so nothing was downloaded.

## 1. Real corpora through `load_documents`

Script: [`0004-real-data-load.py`](0004-real-data-load.py). Text files are checked byte for byte against
the file (after line endings and a byte-order mark); HTML output is checked for leaked markers, unpaired
code fences and near-empty pages. `measured`

| Corpus | Files | Text | Time | Result |
|---|---|---|---|---|
| Kubernetes docs, `content/en/docs/concepts` (Markdown, Hugo) | 191 | 2.30 M chars | 18 ms | text identical to the files |
| CPython `Doc/library` and `Doc/tutorial` (reStructuredText) | 359 | 7.65 M chars | 40 ms | identical; one stray `.html` template almost empty |
| FastAPI docs `docs/en/docs` (Markdown, MkDocs) | 159 | 1.52 M chars | 22 ms | identical |
| Python docs, 15 library pages (HTML) | 15 | 0.90 M chars | 0.4 s | see below |
| Wikipedia, 8 articles (HTML) | 8 | 0.25 M chars | 0.2 s | see below |
| Chroma chunking-evaluation corpora (Markdown) | 5 | 1.44 M chars | 2 ms | identical; 790 of 790 gold spans exact |
| MultiHop-RAG, 609 news articles written out as Markdown | 609 | 6.8 MB | 41 ms | 6,084 of 6,084 evidence facts found verbatim |

**HTML was the weak part.** Before the fix, a Python docs page began with about 40 lines of menus
("Theme Auto Light Dark", "Table of Contents", "Previous topic", "Navigation", breadcrumbs), and a
Wikipedia page with about 90 (the main menu, tools, languages) before its first sentence. With the main
content kept (`<main>`, `role="main"`) and `<nav>` and `<aside>` dropped (D-040), a Python docs page now
starts at its `# json — JSON encoder and decoder¶` heading; Wikipedia still carries its language list,
which is inside `<main>` and is left for the audit's `boilerplate.repeated` check. Real tables came out as
proper rows (`datetime.html`: 79 rows; Wikipedia's infobox as `| Developer | PostgreSQL Global Development
Group |`). `measured`

The reviews of step 1 found HTML that real sites may send and the first version mishandled: an omitted
`</tr>` lost the table and everything after it, an omitted `</head>` hid the whole body, a nested table or
a `<pre>` in a cell broke the row, blank lines in `<pre>` were collapsed. All are fixed and tested
(`tests/unit/test_html_text.py`). `measured`

## 2. What Ollama's `/api/embed` reports

Script: [`0004-real-data-ollama.py`](0004-real-data-ollama.py), Ollama 0.34.4. `measured`

| Model | Context length (`/api/show`) | Cut at, by default | Cut at, `num_ctx` and `num_batch` = context length |
|---|---|---|---|
| `nomic-embed-text` | 2,048 | 2,048 | 2,048 |
| `mxbai-embed-large` | 512 | 512 | 512 |
| `embeddinggemma` | 2,048 | 2,048 | 2,048 |
| `bge-m3` | 8,192 | **2,048** | 8,192 (needs `num_batch`; `num_ctx` alone kept 2,048) |
| `all-minilm` | 512 | **256** (its `num_ctx` parameter) | 512 |

- `prompt_eval_count` is **one count for the whole call**: "hello world" alone is 4 tokens, the second
  text alone 8, both in one call 12. Per-text counts need one text per call.
- One text per call is **not slower**: 128 chunks of 300 words, batches of 32 against one per call:
  nomic 98 vs 95 texts/s, mxbai 52 vs 49, bge-m3 40 vs 42.
- An input over the limit is **cut silently** by default; `truncate: false` returns HTTP 400 "the input
  length exceeds the context length".
- A batch gives the same vectors as single calls (cosine 1.0).

So the design's "the input limit comes from `/api/show`" (§4.3) was wrong for two of five models: a
chunker ranked with `bge-m3` at its advertised 8,192 tokens would have been read only to 2,048 without any
warning. The table in [0002](0002-local-models.md) §3 lists advertised limits, not limits in force. Fixed
in the design (§4.3, §7.1, §11.1) and in the `Embedder` protocol, which now returns token counts with the
vectors (D-041). `measured`

## 3. A first retrieval on real questions

Script: [`0004-real-data-chroma.py`](0004-real-data-chroma.py). Chroma's chunking-evaluation questions
(GPT-4-written, with exact character spans), 800-character chunks, cosine, hit@5 against the first gold
excerpt. Not ragcourt's pipeline (that is step 5); a check of the premise. `measured`

| Corpus (questions) | Quote cut by the chunking | fake embedder | `nomic-embed-text` | `mxbai-embed-large` |
|---|---|---|---|---|
| State of the Union (76) | 14 | 27 | 58 | 62 |
| WikiTexts (144) | 28 | 54 | 107 | 95 |

- About **one gold quote in five is cut** by naive 800-character chunks before any embedder is involved:
  the `chunker.split` blame ragcourt is built to show.
- The **order of embedders changes with the corpus** (mxbai ahead on one, nomic on the other), by margins
  of a few questions: the reason for intervals and per-corpus measurement.
- Among quotes that were not cut, State of the Union saturates (62 of 62 found by three models): Chroma's
  questions are easy, so they cannot separate embedders. Harder categories (D-032) are needed. `inferred`
- The fake embedder (hashed words) finds about half as many: fine for deterministic tests, never a
  stand-in for a real model's numbers. `inferred`

Prefixes ([`0004-real-data-prefixes.py`](0004-real-data-prefixes.py)): the documented query and document
prefixes of nomic, mxbai and embeddinggemma changed hit@5 by −3 to +4 questions in either direction
(D-042). `measured`

## 4. What this changed

D-040 (reading real documents), D-041 (one text per call, the limit in force measured), D-042 (query and
document prefixes); design §4.1, §4.3, §7.1, §11.1; the fixes listed in the change log under "Fixed".
Real datasets for later steps are surveyed in [0005](0005-rag-datasets.md).
