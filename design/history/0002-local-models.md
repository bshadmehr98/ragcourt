# 0002: Local models on the owner's machine (2026-11-22)

The owner answered the first proposal: the first useful result must use a model, any local model that
fits the machine is allowed, Ollama is installed, and a model judge is required. Before redesigning,
this note measures what local models can do here. Evidence levels as in
[0000-research.md](0000-research.md): `measured` means run on this machine today with the script beside
this note ([`0002-local-models.py`](0002-local-models.py)); `inferred` means our reasoning.

## 1. The machine

Intel i9-14900HX (32 threads), 30 GB RAM, NVIDIA RTX 4060 Laptop GPU with 8 GB, Ollama 0.34.4.
Already installed: `qwen3:4b`, `gemma4` (6.6 GB). Pulled for this note: `nomic-embed-text`,
`mxbai-embed-large`, `bge-m3`, `embeddinggemma`, `qwen3-embedding:0.6b`, `all-minilm`, `qwen3:1.7b`,
`llama3.2:3b` (about 7 GB in all). `measured`

## 2. Method

The corpus is the 14 Markdown pages of hone-flow's `docs/` (134 kB, commit `d68cc06`): developer
documentation with prose, tables and code, the kind of corpus ragdoctor is for. Paragraph-packed chunks
of about 1,200 characters (134 chunks). For each chat model: 10 windows sampled with a fixed seed, two
questions each (a paraphrase and a keyword question) with a quote, `temperature 0`; each quote searched
exactly, then whitespace-insensitively; up to 10 kept questions answered with no documents, then graded
by the same model as judge. Each model is unloaded before it is measured, so load time is included.
`measured`

## 3. Embedders

| Model | Load (s) | Chunks / s | Dimension | Input limit (tokens, from `/api/show`) |
|---|---|---|---|---|
| `all-minilm` | 0.9 | 125 | 384 | 512 |
| `nomic-embed-text` | 1.5 | 107 | 768 | 2,048 |
| `mxbai-embed-large` | 1.1 | 59 | 1,024 | 512 |
| `embeddinggemma` | 1.4 | 51 | 768 | 2,048 |
| `bge-m3` | 1.4 | 44 | 1,024 | 8,192 |
| `qwen3-embedding:0.6b` | 1.7 | 8 | 1,024 | 32,768 |

All `measured`. Ollama's `/api/embed` returns `prompt_eval_count`, the number of tokens it embedded, so
chunk sizes in the embedder's own tokens can be measured through Ollama with no tokenizer library (one
chunk per call, or by difference); `/api/show` gives each model's input limit. `measured`

## 4. Chat models: questions with verbatim quotes

| Model | Size | Load (s) | s per window (2 questions) | Quotes found exactly | + with whitespace | Found of generated |
|---|---|---|---|---|---|---|
| `gemma4` | 6.6 GB | 3.9 | 1.3 | 14 | 5 | 19 / 20 |
| `qwen3:4b` | 2.5 GB | 3.9 | 2.2 | 14 | 0 | 14 / 20 |
| `llama3.2:3b` | 2.0 GB | 3.3 | 1.1 | 10 | 3 | 13 / 17 |
| `qwen3:1.7b` | 1.4 GB | 3.0 | 1.0 | 7 | 0 | 7 / 21 |

`measured`. Quality problems seen in every model's output, not only the small ones: keyword "questions"
that are a bare identifier (`--json`, `gates`), quotes that are a line of code (`assert …`) or only a name
(`` `source_changed` ``), and the `style` field often missing. The whitespace-insensitive search
(D-010) recovered 5 of gemma4's 19 quotes. `measured`

`qwen3:4b` ignored `think: false` on this Ollama version and reasoned before every reply, which made its
closed-book answers take 15.5 s each. `measured`

## 5. The judge

Closed-book answer, then a judge's verdict against the quote, same model:

| Model | Closed-book (s / question) | Judge (s / question) | Judge errors seen (of 10) |
|---|---|---|---|
| `gemma4`, first prompt | 0.5 | 0.1 | at least 3: "I need more context" and two generic answers graded correct |
| `gemma4`, strict prompt | 0.5 | 0.3 | none: all 10 answers were refusals or generic, all graded incorrect with a reason |
| `llama3.2:3b`, strict prompt | 0.3 | 0.3 | 2: `UNKNOWN` graded correct; an answer about Git graded correct |
| `qwen3:1.7b`, strict prompt | 0.1 | 0.3 | at least 4: `UNKNOWN` graded correct four times |

Timings `measured`; the error counts are the designer's reading of the verdicts, not a labelled set
(`inferred`). The strict prompt asks for `UNKNOWN` when the answerer does not know and tells the judge
that a refusal, a guess or a generic answer is not correct.

What follows for the design (`inferred`):

- A judge is only as good as the model and the prompt, and small models fail in a recognisable way
  (grading a refusal as correct). The judge must **pass a self-test** on labelled cases before its
  verdicts are used, and code should not ask the judge at all when the closed-book answer is `UNKNOWN`.
- The generator needs a **validity filter** too (is the question a real question, does the quote answer
  it, is the quote prose rather than a bare name): a judge call, plus cheap code rules (a minimum number
  of words in the quote and the question).

## 6. Can a first result come in under a minute?

An estimate for this corpus (134 chunks) with `gemma4` as generator and judge and three fast embedders
(`nomic-embed-text`, `embeddinggemma`, `mxbai-embed-large`): loads about 8 s; 20 windows for about 40
questions, 26 s; validity and closed-book checks on about 38 kept questions, skipping the judge on
`UNKNOWN`, about 20 s; embedding with three models, about 7 s; scoring, under a second. About 60 s, before
any concurrency. `inferred` from the measured parts. Two levers that were not measured: Ollama's
parallel requests (`OLLAMA_NUM_PARALLEL`), and asking several closed-book questions in one call. The
second run on the same corpus reuses the questions and the cached embeddings and takes seconds.

`gemma4` (6.6 GB) and one embedder (under 1.3 GB) fit together in 8 GB of VRAM; switching embedders
reloads only the small model. `inferred` from the sizes; the GPU was otherwise idle.

## 7. Rerankers

Ollama 0.34.4 has no rerank route (`/api/rerank` and `/v1/rerank` return 404). `measured`. Local
reranking therefore needs either a chat model ranking candidates (a listwise prompt over the top 20, one
call per question; about 1 s per question with gemma4, `inferred` from the judge timings) or an
in-process cross-encoder (the `local` extra).

## 8. Not measured

- An end-to-end first-minute run (the pieces were timed separately).
- Judge accuracy on a labelled set; the self-test set has to be written.
- Question quality on prose-heavy corpora (only developer docs were used).
- `gemma4` on a machine with less VRAM, and CPU-only speed (`rr-gemma4-cpu` exists here but was not timed).
- Concurrency in Ollama.
