# ragcourt: the design (0.1)

This is the design as it stands, written from the owner's brief of 2026-11-22
([`history/0001-owner-brief.md`](history/0001-owner-brief.md)) and accepted with
[`changes/0001-initial-design.md`](changes/0001-initial-design.md). Its §16 lists the guarantees the tests
check; §17 says what is built and what is still planned. The smaller choices are in
[`decisions.md`](decisions.md). Section numbers are stable: code comments and the skills refer to them
("design §9.1").

**Status:** accepted by the owner (2026-11-22) after four rounds of answers; being built in one
milestone, and §17 says what is done.

## 1. What it does

ragcourt is a command-line tool for people building retrieval-augmented generation. Given a folder of
their own documents, it **audits** how a chunker cuts them (no model needed), **ranks** chunkers,
embedding models, retrievers and rerankers by measuring them against questions whose gold answers are
exact quotes from the documents, **explains** each failed question by naming the one stage that lost it
and what would fix it, and lets a model act as a **doctor** that proposes, and may write, a chunker that
is then measured like any other. It runs on **local models** through Ollama out of the box, or on any
OpenAI-compatible endpoint the user configures. Code decides every number and every blame; a model
writes questions, a **judge** model filters them, and in `doctor` a model makes suggestions.

### Goals

- A useful result with no API key, on local models through Ollama: `audit` in seconds; the full ranking
  after a one-time `setup`, with its time shown before it starts and its progress while it runs. The
  brief's "under a minute" was dropped by the owner: trustworthy numbers need about 540 questions,
  written once per corpus (D-006, D-034).
- Numbers measured on the user's documents, with their uncertainty, never general advice (brief §1, §5).
- Every failed question has one named cause and a suggested fix (brief §1, §4).
- A newcomer reads the whole codebase in an evening and adds a stage in one file (brief §1, §7, §9).
- **Nothing happens blindly** (owner, D-030): before a model is called, the user is told in plain words
  which model does what, what it is shown, how it is judged and how to change it; every verdict keeps its
  reason; every number and every blame comes with the rule that produced it.

### Non-goals (0.1)

Answer generation and judging generated answers; vector databases (indexes are in memory);
images, audio, video and scanned documents; a hosted service; telemetry; a web server; a full grid
search; fine-tuning anything (brief §11, with model judges allowed by the owner's answer, D-012).

### Who it is for

A developer with a few dozen to a few thousand documents (up to roughly 50 MB of text) who must choose
a chunker, an embedding model, a retriever and a reranker, and wants evidence from their own corpus.

## 2. Concepts and words

| Word | Meaning |
|---|---|
| **document** | one source file loaded as text, with a stable id (its path relative to the corpus folder) |
| **span** | a `[start, end)` pair of character offsets into one document's text |
| **chunk** | a string a chunker returned, with the span the pipeline found for it (§4.2) |
| **stage** | one implementation of one of four **kinds**: chunker, embedder, retriever, reranker (§7) |
| **your pipeline** | a retrieval system ragcourt did not build, registered as one function from a question to ranked chunk texts; ragcourt only questions it (§7.5) |
| **pipeline** | one chunker, one embedder (or none, for a lexical retriever), one retriever and one reranker (or none) |
| **question** | a question with its **gold quote**: a span of one document that answers it (§6) |
| **split** | `dev` (used to choose) or `held-out` (used to report) (§6.4) |
| **hit** | a chunk whose span contains the whole gold quote (§8.2) |
| **depth** | how many candidates the retriever returns: 50 (brief §4) |
| **k** | how many chunks the pipeline returns in the end: 5 by default |
| **miss** | a question with no hit in the top k |
| **category** | the kind of question, each testing one weakness: `paraphrase`, `keyword`, `exact_term`, `distractor`, `negation`, `numeric`, `user` (§6.7) |
| **blame** | why a miss happened: a stage (`chunker`, `embedder`, `retriever`, `ranking`), a mechanism inside it, its evidence and an evidence level (§9) |
| **twin passage** | for a `distractor` question, the similar passage that does not answer it (§6.7) |
| **ceiling** | the best Hit@k a pipeline could reach if every stage after a given one were perfect (§9.2) |
| **check** | one audit rule with a stable code, such as `cut.mid_sentence` (§5.1) |
| **measured / estimated** | a token count from the embedder's own tokenizer, or from the fallback estimate (§4.3) |
| **run** | one `rank` invocation: its plan, its estimate, its results file (§13.3) |
| **local model** | a model served by Ollama on this machine (§11.1) |
| **judge** | a chat model that grades a closed-book answer or a question's validity against the quote; never used for blame or metrics (§6.6) |

## 3. Architecture

One Python package, `ragcourt`, standard library only in its core (D-003). No services, no framework.

### 3.1 Layers

```text
types, errors, text_units   layer 0  dataclasses and protocols, no logic; the reference units of text
stages                      layer 1  the registry, its shared modules, one file per stage
core   |   io               layer 2  core: pure functions; io: files, the model client, the cache, reports
flows                       layer 3  parts of commands that several commands share (D-045)
commands                    layer 4  one file per command
cli                         layer 5  argument parsing
```

A module imports only from layers below its own. `core` and `io` never import each other: a flow or a
command reads with `io`, computes with `core`, and writes with `io`. Within `stages`, an implementation
(`stages/<kind>s/<name>.py`) imports only the registry and its shared modules (`stages/specs`,
`stages/splitting`, `stages/loader`), never another implementation; only the pipeline joins stages. A
command never imports another command; what two commands share (building the question set, evaluating a
pipeline, the judge's self-test) is a flow. Nothing imports `cli` (except `__main__`) or `testing`. The
package root (the public API) may import from every layer except `flows`, `commands` and `cli`.
`scripts/check_layers.py` enforces all of this and runs in `scripts/check.sh`.

`core` is pure in this sense: its functions take values and callables and return values; they never open
files, read the clock or the environment, or touch the network. The callables they receive (an embedder's
`embed`, a chat model as prompt-in reply-out) may do I/O; `core` does not know. `text_units` (layer 0)
holds the reference tokenization and sentence rules, so chunkers (layer 1) and metrics (layer 2) count
alike (D-043).

Stages that need a model (the Ollama and endpoint embedders, the `llm` and endpoint rerankers) receive the
client through the `ModelClient` protocol declared in `types` (§11.1): a factory or function that has a
`client` parameter is given it, so stages never import `io`.

### 3.2 Modules

Small modules of one concept each (CONTRIBUTING.md "Keep it simple", D-036): where the design has a list
of similar things (stages, audit checks, question categories, blame mechanisms, commands), each is its
own file and the package's `__init__.py` holds the ordered list.

| Module | Holds | Design |
|---|---|---|
| `types/documents.py`, `stages.py`, `models.py`, `config.py`, `audit.py`, `questions.py`, `results.py` | frozen dataclasses and protocols; no logic | §2 |
| `errors.py`, `text_units.py` | `RagCourtError` and its subclasses; reference tokens and sentences | §14, §4.3 |
| `stages/__init__.py`, `loader.py`, `specs.py`, `splitting.py` | the decorators and registry; loading built-ins and the user's folder; `name:key=value` specs; span arithmetic the chunkers share | §7 |
| `stages/<kind>s/<name>.py` | one stage per file | §7.3, §7.4 |
| `core/offsets.py`, `core/chunking.py`, `core/structure.py`, `core/sizes.py`, `core/boundaries.py` | spans of chunks; a corpus cut by one chunker; headings, tables, code; size summaries; boundaries marked | §4, §5 |
| `core/audit/<check>.py` | one audit check per file; `__init__.py` lists them | §5.1 |
| `core/windows.py`, `core/words.py`, `core/categories/<category>.py` | passages offered to the writer; content words; one category per file | §6.1, §6.7 |
| `core/generate.py`, `core/question_checks.py`, `core/question_rules.py`, `core/verdicts.py`, `core/split.py`, `core/selftest.py`, `core/user_questions.py` | the question loop; its checks; the code rules; reading replies; dev and held-out; the judge's self-test; your questions | §6 |
| `core/pipeline.py`, `core/relevance.py`, `core/metrics.py`, `core/stats.py`, `core/leaderboard.py` | one pipeline over the questions; hits and tokens; every metric; intervals and ties; leaderboards | §8 |
| `core/blame/<stage>.py`, `core/blame/facts.py`, `core/fixes.py`, `core/ceilings.py` | the mechanisms of one stage, in order; what blame looks at; fixes and levels; ceilings | §9 |
| `core/search.py`, `core/plan.py`, `core/recommend.py`, `core/doctor.py` | the greedy steps and the choice on dev; the estimate; the models that fit a machine; doctor's pure parts | §10, §11.3, §12 |
| `io/documents.py`, `io/html_text.py`, `io/pdf_text.py`, `io/config.py`, `io/toml_edit.py`, `io/config_template.py` | reading documents and HTML; `ragcourt.toml`, editing a role, the commented template | §4.1, §3.3, §11.4 |
| `io/http.py`, `io/client.py`, `io/ollama.py`, `io/openai_compat.py`, `io/replies.py`, `io/embedders.py` | JSON over HTTP with retries; the one client and its two dialects; building embedders by name | §11.1 |
| `io/cache.py`, `io/question_file.py`, `io/judge_record.py`, `io/run_files.py`, `io/prompts.py` | the plain files: embeddings, questions, the judge's self-test, runs, prompts | §6.5, §6.6, §10, §13.3 |
| `io/terminal.py`, `io/narration.py`, `io/audit_output.py`, `io/question_output.py`, `io/rank_output.py`, `io/explain_output.py`, `io/result_data.py`, `io/html_report.py` | everything written for people, rendered from data | §13 |
| `io/project.py`, `io/ask.py`, `io/machine.py`, `io/isolated_run.py` | a command's view of the project; asking before what cannot be undone; memory of the machine; running generated code apart | §3.3, §11.3, §12 |
| `core/external.py`, `flows/external.py`, `core/blame/retrieval.py` | the user's own pipeline: its texts placed in the documents; asked, scored and blamed | §7.5 |
| `flows/audit.py`, `flows/questions.py`, `flows/judge.py`, `flows/evaluate.py`, `flows/probes.py`, `flows/blames.py`, `flows/run_plan.py`, `flows/rank.py`, `flows/search_steps.py`, `flows/results.py`, `flows/doctor.py` | the parts of `questions`, `rank` and `doctor` | §6 to §12 |
| `commands/<command>.py` | one command per file | §13.1 |
| `demo/results.json`, `demo/recording.json` | the recorded real run `ragcourt demo` replays, and when, where and how it was made | §13.1 |
| `prompts/*.txt`, `prompts/judge_cases.jsonl` | every prompt a model is given, and the judge's labelled self-test cases | §6.6 |
| `cli.py`, `__main__.py` | `ragcourt …`, `python -m ragcourt` | §13.1 |
| `testing/` | the fake embedder, the scripted model and replies, fake Ollama and endpoint servers, `offline_project`, the bundled corpus | §15.2 |

### 3.3 Files

Everything ragcourt writes goes in `.ragcourt/` beside the corpus (or `--workdir`), as plain files a
user can open; there is no database (D-016): `cache/embeddings/` (§10.2), `questions.jsonl` (§6.5),
`runs/<run-id>/` with `progress.jsonl`, `results.json` and `report.html` (§10.4, §13), `doctor/` (§12). The optional `ragcourt.toml` in the project names endpoints, models, prices, stages to
consider, `k` and the budget; keys are named by environment variable (`api_key_env = "OPENAI_API_KEY"`),
never written in the file (D-016).

## 4. Documents and chunks

### 4.1 Loading documents

`.md`, `.markdown`, `.txt`, `.rst` and `.html`/`.htm`, and `.pdf` with the extra `pdf` (below). HTML is read with the standard library's
`html.parser` into Markdown-shaped text: headings as `#` lines, tables as `| a | b |` rows under a
`| --- |` line, `<pre>` as fenced code, so the audit reads it like Markdown; end tags HTML lets authors
leave out are closed where a browser would close them; when the page marks its main content (`<main>`
or `role="main"`) only that is kept, and `<nav>` and `<aside>` are always dropped, so a site's menus do
not become part of every document (D-040). Files are read as UTF-8, a leading byte-order mark dropped; a
file that is not UTF-8 or cannot be read is reported and skipped, never guessed. Line endings are
normalised to `\n`; nothing else in the text is changed, so offsets are offsets into what the user wrote
(an external set of gold offsets, such as Chroma's, matched 790 of 790). Hidden files and folders and
`.ragcourt/` are skipped; a link to a folder is reported, not followed.

**PDF** (change 0005, D-059): with `pip install 'ragcourt[pdf]'` a PDF's document is the text `pypdf`
extracts, page by page, the pages joined by a blank line, line endings normalised and nothing else changed
(no words re-joined at line ends, no running header removed). Offsets, quotes and chunks refer to that
text, as an HTML page's refer to its extracted text, so gold stays verbatim in what every chunker was
given. `audit` says how many documents came from PDF and names the extractor and its version; `audit
--show` prints the text. A PDF that cannot be read is skipped with its reason: no text (scanned),
encrypted, damaged, over 50 MB or 5,000 pages; without the extra, each PDF is skipped with the install
command. Nothing inside a PDF is run or opened.

### 4.2 Offsets: from strings to spans

A chunker returns strings; the pipeline finds where each one is (brief §7):

1. Search for the chunk's text in the document starting at the previous chunk's start + 1 (so overlapping
   chunks are found, and repeated text is matched in reading order).
2. If not found exactly, search again with runs of whitespace treated as equal (a chunker that strips or
   joins lines still maps back); the span covers the original characters.
3. If still not found, the chunker is invalid for this document: `ChunkNotInSource` names the chunker,
   the document, the chunk's index and its first 80 characters. A chunker that changes words, adds text
   (a heading prefix, a summary) or reorders text cannot be evaluated in 0.1 (§18; D-010).

Empty and whitespace-only strings are dropped and counted. Chunks are kept in the order returned.

### 4.3 Token counts

Chunk sizes are counted in the **embedder's own tokens** (brief §5), and an embedder returns them with
the vectors (`Embedded`, §7.1). For an Ollama embedder each text is sent in its own call, because Ollama
reports one `prompt_eval_count` per call, not per text; one text per call measured no slower than
batches (D-041). The input limit **in force** is not simply `/api/show`'s context length: Ollama cuts
the input silently at the smallest of the context length, the request's `num_ctx` and its `num_batch`
(`bge-m3` advertises 8,192 tokens and used 2,048 by default; `all-minilm` 512 and 256). The `ollama`
embedder sets both options to the context length, and measures the limit in force once per model with an
over-long probe text, whose count is the limit; that measured limit is what `size.over_limit` and
`chunker.over_limit` use. The `endpoint` embedder counts with `tiktoken:<encoding>` when told to (the
optional `tokens` extra); an embedder of your own may return its own counts. When no count can be
loaded, sizes use the fallback estimate (characters / 4) and every size and every "over the limit" flag
from it is labelled **estimated** in every output; a measured count is labelled **measured** (D-008).

Token-level metrics against the gold quote (§8.3) use a separate, fixed **reference tokenization** (words
and punctuation by a regular expression, on the source text), so they are comparable across embedders
(D-009).

## 5. Audit

`ragcourt audit <folder> [--chunker NAME[:k=v,…]]… [--embedder NAME] [--show DOC]`. No key and no
chat model. With no `--chunker`, every built-in native chunker is audited with its defaults. Sizes and
the input limit come from the embedder: by default the first default local embedder through Ollama
(measured, §4.3), or `--embedder`. When no embedder is reachable the audit still runs, sizes are
labelled estimated, and `size.over_limit` uses the limit from the built-in table of known models or is
skipped with a note.

### 5.1 Checks

Each check is one file in `core/audit/`, listed in its `__init__.py`, with a stable code (brief §2; D-024 for the
thresholds, all overridable in `ragcourt.toml`):

| Code | Flags a chunk that… |
|---|---|
| `cut.mid_sentence` | ends where the source continues the same sentence: the last non-space character is not sentence-ending punctuation, a closing bracket or quote, or the end of a block (a blank line, a heading, the end of the document) |
| `context.no_heading` | lies under a heading (Markdown `#`, setext, or HTML `h1`–`h6`) that appears neither in the chunk nor, for the chunk's first section, at its start |
| `split.table` | contains part, but not all, of a Markdown or HTML table's rows |
| `split.code` | contains part, but not all, of a fenced or indented code block |
| `boilerplate.repeated` | consists mostly (≥ 50% of its lines) of lines that repeat across ≥ 30% of the documents (headers, footers, navigation) |
| `duplicate.near` | has word-5-gram Jaccard similarity ≥ 0.9 with an earlier chunk (MinHash-free exact shingles below 20k chunks, a fixed-seed MinHash above) |
| `size.tiny` | has fewer than 20 tokens |
| `size.over_limit` | has more tokens than the embedder accepts, so the end would be silently truncated (measured or estimated, §4.3) |

### 5.2 Output

A summary table per chunker: chunks, size in tokens (median, p95, max, labelled measured or estimated),
and the count and share of chunks per check. Then the worst examples per check (document, offsets, the
first and last 60 characters). `--show DOC` prints the document with chunk boundaries marked inline
(`⟦12⟧` at each start, `⟧` at each end, flagged chunks named), so the user sees the cuts on their own
text. `--json` writes the same as data. The exit code is 0, or 3 with `--fail-on CODE…` when one of those
checks fires (for CI).

## 6. Questions and gold answers

### 6.1 Generation

`ragcourt rank` (or `ragcourt questions` alone) asks the question writer to write questions: the
default local chat model (D-027), or the configured one.
Questions are written **by category** (§6.7), because one mixed set cannot say which embedder is good
at what. For each category, passages are chosen from the documents by code (not from any chunker's
output: brief §3), with a fixed seed: windows of about 2,000 characters cut at paragraph boundaries that
can support that category (§6.7). For each window the writer gets the category's prompt and returns JSON
`{question, quote}` (and, for some categories, the term or the twin passage it used). The prompt asks for
a quote of one to three sentences that answers the question on its own. How many questions are wanted,
per category, is in §6.8.

### 6.2 Validation and filters

Applied in order, each drop counted by reason and reported:

1. **Not verbatim:** the quote is searched in the window's document, first exactly, then with
   whitespace runs treated as equal (D-010). Not found: dropped (brief §3). Found: the gold is the span.
2. **Code rules** (D-028): a quote of fewer than 6 words, with no sentence (a bare name, a single line of
   code) or over 120 reference tokens; a question of fewer than 3 words outside `keyword`.
3. **Not of its category:** the code check of the category fails (§6.7); for `negation` and `distractor`
   the judge must also confirm it.
4. **Duplicate:** a question whose quote overlaps an earlier question's quote by more than half, or whose
   text is a near-duplicate of an earlier question.
5. **Not valid** (judge, §6.6): the judge is asked whether the question is a real question a user could
   ask and whether the quote answers it; "no" drops it.
6. **Answerable without the documents** (judge, §6.6): the question writer answers with no documents and
   is told to reply `UNKNOWN` when it does not know. `UNKNOWN` keeps the question without a judge call;
   any other answer goes to the judge with the quote, and an answer graded correct drops the question
   (D-012).

Each kept and dropped question stores its verdicts with the judge's reasons, so the user can read why.

The question set never refers to chunks; it depends only on the documents' text. If a document changes,
its questions are revalidated against the new text and dropped when the quote is gone.

### 6.3 The user's own questions

`--questions-file my.jsonl`: one JSON object per line with `question` and `quote`, and optionally
`document` (otherwise every document is searched; a quote found in more than one place is rejected as
ambiguous unless `document` is given). They are validated by rule 1 only and tagged `category: user`; user
questions are never dropped by the judge (D-025). A question without a quote
cannot be scored and is rejected with that reason (D-025).

### 6.4 Splits

Each question gets a split from a hash of its id and the run's seed: one third `dev`, two thirds
`held-out` (30 and 60 of the default 90 per category, §6.8), within each category and spread over the
documents. The search (§10) reads only dev results: choosing needs fewer questions than measuring
precisely, and ties on dev are broken by cost. Every number in a leaderboard, every interval and every
blame in `explain` is from held-out questions (D-011, D-032).

### 6.5 The question file

`.ragcourt/questions.jsonl`, first line a header `{"format_version": "1", "corpus_hash": …, "model": …,
"seed": …, "dropped": {category: {reason: count}}}`, then one question per line: `id`, `question`, `category`, `term` or `twin` where the
category has one,
`document`, `start`, `end`, `quote`, `split`. Reused by later runs while the corpus hash matches; a newer
`format_version` is refused with a message.

### 6.6 The judge

A judge is a chat model (by default the question writer; `--judge MODEL` for another) asked one of two
fixed, versioned prompts: **validity** (is this a real question, and does the quote answer it?) and
**closed-book** (does this answer state the specific fact the quote gives? a refusal, `UNKNOWN`, a guess or
a generic answer is not correct). It replies JSON `{verdict, reason}`; a reply that is not valid JSON is
retried once, then the question is kept and the failure counted.

Before its verdicts are used, a judge passes a **self-test** (D-026): about 40 labelled cases bundled with
ragcourt (correct, wrong, generic and refused answers; valid and invalid questions). Below 90% agreement
the model is refused as judge, its errors are shown, and the run stops with a message naming better
candidates. The result is cached per model and prompt version and printed in every run's output.

Judges filter questions and, as the `llm` reranker (§7.3), may order candidates. They never decide blame
(§9) or compute a metric (§8).

**What the user sees** (D-030). A new user is never left to guess what the judge did:

- **Before the first judge call** of a run, a short paragraph in plain words: which model is the judge and
  why (default, `ragcourt.toml` or a flag); the two things it is asked; exactly what it is shown (the
  question, the quote, and for the closed-book check the answer given without the documents) and what it
  is never shown or asked (the chunks, the scores, the blame); and the commands to read more.
- **The prompts are readable files** shipped in the package (`prompts/*.txt`), printed with
  `ragcourt prompts show judge.validity` and `judge.closed_book`. A user may replace them (`prompts_dir`
  in `ragcourt.toml`); a replaced prompt is named in every output with its hash, and the self-test runs
  again on it.
- **The self-test is shown case by case** the first time a judge is used and whenever asked
  (`ragcourt models test judge`): each labelled case, the expected verdict, the judge's verdict and reason,
  agree or disagree, then the score against the 90% bar. The cases are a readable file too.
- **Every verdict keeps its reason.** After filtering, the output shows a table of kept and dropped
  questions by reason with two examples of each; `ragcourt questions show [--dropped] [--reason R]` lists
  every question with its verdicts and reasons.
- [`docs/judge.md`](../docs/judge.md) explains all of this with real output from the bundled corpus.

The same applies to every model role (§11.4): the question writer, the `llm` reranker and doctor each say
what they are given and what they return before they are first called in a run.

### 6.7 Question categories

Each category targets a known weakness of retrieval, so a leaderboard can say "this embedder loses
exact identifiers" instead of one blurred average (D-032; tried with a local model in
[`history/0003-question-categories.md`](history/0003-question-categories.md)). Passages that cannot
support a category are not offered for it, and membership is checked, not assumed:

| Category | Tests | Passages offered (by code) | Membership checked by |
|---|---|---|---|
| `paraphrase` | the same meaning in different words | any | code: content-word overlap of question and quote below 0.15 |
| `keyword` | a few search terms, no sentence | any | code: 2 to 6 words, no question mark |
| `exact_term` | a rare identifier, name, code or number with its unit, which embedders blur | windows holding a term found in one document only and shaped like an identifier, a name or a number with a unit; the term is chosen by code and given to the writer | code: the term is in the question and the quote |
| `distractor` | a question worded like another passage that does not answer it (misleading) | pairs of windows with high word overlap (twins), chosen by code; the writer gets both | code: the question shares more words with the twin than with its own passage; judge: the twin does not answer it |
| `negation` | what is not done, never allowed, the exception | windows with a negation or an exception in the text | code: a negation in question and quote; judge: the quote answers the negated question |
| `numeric` | a number, default, limit, version or date | windows with a number in prose | code: the number in the quote answers it (the quote holds a number); judge: it is the asked value |
| `user` | the user's own questions (§6.3) | — | quote found |

The twin passage of a `distractor` question and the term of an `exact_term` question are stored with the
question, so blame can name them (§9.1). Categories are switched on and off in `ragcourt.toml`
(`questions.categories`); adding one is a small design change: a prompt file, a passage rule and a
check.

### 6.8 How many questions

The default is **90 questions per category** (30 dev, 60 held-out; `questions.per_category`), for every
category the corpus can support: about 540 for six categories. Generation runs until each category has
its count or its passages are used up (at most 6 requests per wanted question, since hard categories
are accepted 1 to 3 times in 8 without passage selection). The output says, per category, how many were
asked for, written, dropped by reason and kept; a category with fewer than 30 held-out questions is
reported as **too few to rank** with its count, never folded into the average. Questions are written once
per corpus and reused; the plan (§10.3) shows the time this takes before it starts (44 minutes on the
owner's machine for the 434 questions the FastAPI docs gave, `measured`, D-057).

**A quick look** (`rank --quick`, change 0004): 20 questions per category. Every category is then too few
to rank, so every board is indicative and names no winner; blame, ceilings and the report work as in any
run. The plan says this before any model is called, and the summary names the full run, which reuses the
questions (D-047).

Every leaderboard also prints, per category, the **smallest difference it can tell apart** at that size
(from the paired bootstrap of §8.4: half the width of the interval of the difference between the top
two), so "no significant difference" comes with "differences under N points cannot be seen with 60
questions".

## 7. Stages

### 7.1 The four kinds

| Kind | Signature (in `types`) | Notes |
|---|---|---|
| chunker | `(text: str) -> list[str]` | the pipeline finds offsets (§4.2) |
| embedder | an `Embedder`: `model`, `max_tokens`, `tokenizer`, `embed(texts, *, as_query=False) -> Embedded` (vectors and token counts) | `as_query` lets a model use its query prefix (D-042); never caches (the cache wraps it, §10.2) |
| retriever | `(chunks: list[str], vectors: list[list[float]] \| None, embed_query) -> search(query, depth) -> list[(index, score)]` | builds its index once per chunk set |
| reranker | `(query: str, candidates: list[str]) -> list[float]` | scores; the pipeline sorts |

Each takes its parameters as keyword arguments with defaults (`recursive:size=512,overlap=64`). Ties in
scores are broken by chunk index, so results are deterministic.

### 7.2 Registration and the user's folder

```python
from ragcourt.stages import chunker

@chunker("by_paragraph")
def by_paragraph(text: str, min_chars: int = 200) -> list[str]:
    ...
```

`@chunker`, `@embedder`, `@retriever` and `@reranker` register a function (or, for an embedder, a factory
returning an `Embedder`) under a name; registering a name twice is an error that names both files. The
built-ins are imported from `stages/<kind>/`; the user's own are loaded from `ragcourt_stages/` in the
project (or `--stages DIR`), every `.py` file in it imported in sorted order. These are the user's own
code and run in-process like any Python they write (D-018); code written by a model is different (§12).

### 7.3 Built-in stages

| Kind | Name | Needs |
|---|---|---|
| chunker | `fixed` (tokens, with overlap) | — (uses the embedder's tokenizer, or the estimate) |
| chunker | `recursive` (paragraphs, lines, sentences, words, down to a size) | — |
| chunker | `sentence` (whole sentences packed to a size) | — |
| chunker | `markdown` (sections by heading, heading kept, then `recursive` inside) | — |
| embedder | `ollama` (any Ollama embedding model; measured token counts and limit) | Ollama |
| embedder | `endpoint` (any OpenAI-compatible `/embeddings`) | an endpoint |
| retriever | `dense` (cosine, exact, in memory) | an embedder |
| retriever | `bm25` (pure Python) | — |
| retriever | `hybrid` (reciprocal-rank fusion of `dense` and `bm25`) | an embedder |
| reranker | `none` | — |
| reranker | `llm` (a chat model orders the top 20 in one listwise call; Ollama has no rerank route) | a chat model (D-015) |
| reranker | `endpoint` (a `/rerank` endpoint in the Jina/Cohere format: vLLM, llama.cpp, TEI, Jina, Cohere) | an endpoint (D-015) |

### 7.4 Adapters and extras

Thin adapters, each one file, each behind an optional extra imported only inside the function:

| Extra | Brings | Stages |
|---|---|---|
| `tokens` | `tiktoken` | exact token counts for the `endpoint` embedder (§4.3) |
| `pdf` | `pypdf` | reading `.pdf` documents (§4.1) |
| `local` | `sentence-transformers` | embedder `st` and reranker `cross-encoder`, in-process (D-007) |
| `chonkie` | `chonkie` | chunkers `chonkie.token`, `chonkie.sentence`, `chonkie.recursive`, `chonkie.semantic` |
| `langchain` | `langchain-text-splitters` | chunkers `langchain.recursive`, `langchain.markdown` |

A missing extra gives `ExtraMissing` naming `pip install 'ragcourt[<extra>]'`.

### 7.5 Your own pipeline (change 0006)

A fifth kind, `pipeline`, is a retrieval system ragcourt did not build:

```python
from ragcourt.stages import pipeline, pipeline_chunks

@pipeline("mine")
def mine(query: str, depth: int) -> list[str]: ...   # your chunk texts, best first

@pipeline_chunks("mine")                              # optional: every chunk your system holds
def mine_chunks() -> list[str]: ...
```

`rank DOCS --pipeline mine` runs the search and then a last step, `pipeline`: the function is called once
per question with the question's text and depth 50, and its held-out numbers are put on a board beside the
search's chosen pipeline, with the tie rule of §8.4. `--no-search` skips the four steps, so no embedding
model is needed. One pipeline per run. It is one fixed system: nothing is chosen on dev.

- **Spans:** each distinct returned text is searched in every document (§4.2). Found in one place: that is
  its span. Not found (rewritten, or a title or summary added), or found in more than one place (its place
  is unknown): it cannot be scored; it keeps its rank, holds no quote and covers no tokens, and both counts
  are printed under the board and kept in the results. When no text at all is found, the run stops.
- **The run is about the pipeline:** `chosen` in the results, the ceilings, the blames, `explain` and the
  report are the user's pipeline's; `search_chosen` names the search's choice. The audit summary of the
  chosen chunker is left out.
- **Blame** (§9.1) uses only what spans and ranks show: the `chunker` mechanisms `too_small`, `split` and
  `dropped` when the chunks are listed; the stage `retrieval` with the one mechanism
  `retrieval.not_found` (a chunk holds the quote, or the chunks are not listed, and the pipeline does not
  return it), with BM25's rank over the listed chunks as its probe; then the `ranking` mechanisms. The
  `embedder` and `retriever` stages are never blamed: ragcourt cannot see inside. A blame is `confirmed`
  when a pipeline ragcourt measured in the same run hits the question (the fix names it), else `indicated`.
- **The plan** names the pipeline and its file, says it is called once per question with the question's
  text, that what it contacts is the user's business, and whether its chunks are listed. Its time is not in
  the estimate. On `--resume` it is asked again.

## 8. The pipeline and metrics

### 8.1 Running one pipeline

For a pipeline and a question set: chunk every document and find spans (§4.2); embed every chunk
through the cache (§10.2); build the retriever; for each question, retrieve `depth` = 50 candidates,
rerank them if a reranker is set, and keep the order. The pipeline returns, per question, the ranked
chunk spans with their scores, the retrieval rank and the final rank of the first hit, and timing.
Everything after the embedding calls is in `core` and deterministic.

### 8.2 Relevance

A chunk is a **hit** for a question when its span (in the quote's document) contains the whole quote.
For graded and token measures, a chunk's relevance is the fraction of the quote's reference tokens inside
its span (D-013).

### 8.3 Metrics

Per question, then averaged over held-out questions:

| Metric | Definition |
|---|---|
| `hit_at_k` | 1 if a hit is in the top k |
| `mrr` | 1 / rank of the first hit in the top `depth`, else 0 |
| `ndcg_at_k` | nDCG over the top k with graded relevance (§8.2); ideal = the best k chunks of this chunking |
| `recall_at_k` | share of the quote's reference tokens covered by the union of the top-k spans |
| `token_precision_at_k` | quote tokens in the top-k spans / all tokens in the top-k spans (overlaps counted once) |
| `token_iou_at_k` | quote tokens covered / (quote tokens ∪ tokens of the top-k spans) |
| `recall_at_budget` | `recall_at_k` with chunks taken in rank order until a fixed budget of reference tokens (default 400; the last chunk is cut at the budget), so large chunks cannot win by size (brief §5) |

And per pipeline: `vectors` (chunks embedded), `chunk_tokens` (median and p95, measured or estimated),
`tokens_per_query` (tokens in the top k), `latency_ms` (p50 and p95 per query, excluding cached
embedding), `index_ms`, and `cost` (from the user's prices per million tokens; `unknown` when a price is
not given, never 0; D-020).

### 8.4 Uncertainty and ties

Every averaged metric is reported **per category** (§6.7) and **overall**, with a 95% interval from a
bootstrap over held-out questions (2,000 resamples, fixed seed). Overall is the mean of the category
means, so every category weighs the same whatever its size; a category too few to rank is left out and
named. The leaderboard is sorted by the chosen metric (`recall_at_budget` by default;
`--metric`). The top two are compared with a **paired** bootstrap of the per-question difference: if its
95% interval contains 0, the output says "no significant difference" between them, lists every entry
not separable from the top the same way, and calls none of them the winner. A smaller or cheaper entry
among the tied is pointed out as such (D-011). Ties are decided per category too: an entry can be tied
overall and clearly better on `exact_term`, and the output says so.

## 9. Blame and explain

Telling a user *why* a question was missed is the reason to use ragcourt, so blame is more than a stage
name (D-033). For every held-out miss it gives a **stage**, a **mechanism** inside that stage, the
**evidence** (numbers from the run), an **evidence level**, and a **fix**. All of it is computed by code
from spans, ranks, scores and a few extra measurements (the probes of §9.4); no model is asked.

### 9.1 Blame: a stage and a mechanism

The checks run in this order; the first that holds is the **cause**, and every later one that also holds
is listed as **also seen**. A miss always gets exactly one cause.

**Stage `chunker`: no chunk holds the whole quote, or the chunk that holds it hides it.**

| Mechanism | Holds when | Evidence shown |
|---|---|---|
| `chunker.too_small` | the quote is longer than the chunker's largest chunk | quote and chunk sizes in tokens |
| `chunker.split` | the quote is cut across a chunk boundary | the boundary on the text, the words each side |
| `chunker.dropped` | part of the quote is in no chunk at all | the characters no chunk covers |
| `chunker.over_limit` | a chunk holds the quote, but the quote lies past the embedder's input limit inside it, so the embedder never read it | the quote's token position, the limit (measured, §4.3) |
| `chunker.diluted` | a chunk holds the quote, but the quote embedded on its own would reach the top 50 while the chunk does not: the answer is drowned in a long or mixed chunk | similarity of query to quote, to chunk, and of the 50th result |

**Stage `embedder`: the chunk is clean, but the embedding model does not bring it into the top 50**
(with a dense or hybrid retriever).

| Mechanism | Holds when | Evidence shown |
|---|---|---|
| `embedder.exact_words` | keyword search (BM25 on the same chunks) puts the chunk in the top 50 and the embedder does not: the embedder blurs the exact words (typical of `exact_term` and `keyword` questions) | the chunk's BM25 rank and dense rank; the term, if any |
| `embedder.distracted` | the question's twin passage (a `distractor` question) or chunks very similar to it fill the ranks above the chunk | the twin's rank, the chunk's rank |
| `embedder.meaning` | neither the chunk nor the quote alone reaches the top 50 with this embedder, and keyword search does not find it either: the model does not connect the question to its answer | the quote-alone rank, the ranks under every other measured embedder |

**Stage `retriever`: the search method, not the vectors.**

| Mechanism | Holds when | Evidence shown |
|---|---|---|
| `retriever.keyword_only` | the retriever is `bm25`, it misses the chunk, and dense search with a measured embedder finds it | both ranks |
| `retriever.fusion` | the retriever is `hybrid`, one of its two lists has the chunk in the top 50, and the fused list does not | the rank in each list and after fusion |
| `retriever.crowded` | more than half of the top 50 are near-duplicates (audit `duplicate.near`) and the chunk is just below | the duplicates' count, the chunk's rank |

**Stage `ranking`: the chunk is in the top 50 but below k.**

| Mechanism | Holds when | Evidence shown |
|---|---|---|
| `ranking.reranker_demoted` | the chunk was in the top k before the reranker, and the reranker pushed it out | ranks before and after |
| `ranking.distracted` | the chunks above it include the question's twin passage | the twin's rank and the chunk's |
| `ranking.duplicates` | the k slots are taken by near-duplicates of one another | the duplicates |
| `ranking.not_rescued` | the chunk was below k before reranking and stayed there (or no reranker is set) | ranks before and after (or "no reranker") |

The search is exact (no approximate index in 0.1), so the retriever can lose a chunk only by its method,
never by approximation.

### 9.2 Ceilings

For the chosen pipeline, per category and overall, on held-out questions: the **chunker ceiling** (an
intact, readable quote in some chunk: no `chunker` cause), the **retrieval ceiling** (that chunk in the top
50) and **Hit@k**. They are non-increasing by construction, and each gap is the share lost to a stage, with
its interval. Counts per mechanism are shown per category ("of 60 `exact_term` questions, 21 lost to
`embedder.exact_words`").

### 9.3 Fixes and evidence levels

A fix comes from the mechanism and, wherever possible, from a measurement already made in the run:

| Mechanism | Fix |
|---|---|
| `chunker.too_small`, `chunker.split`, `chunker.dropped` | the measured chunker that keeps this quote whole and readable, preferring the one that changes least |
| `chunker.over_limit` | a smaller chunk size, or a measured embedder with a longer input limit |
| `chunker.diluted` | a smaller or section-aware chunker that measured better on this question |
| `embedder.exact_words` | `hybrid` retrieval, or the measured embedder that finds it |
| `embedder.distracted`, `ranking.distracted` | a reranker, or the measured embedder that ranks the right passage above its twin |
| `embedder.meaning` | the measured embedder that finds it; if none does, "no tested embedder connects this question to its answer" |
| `retriever.keyword_only`, `retriever.fusion` | the measured retriever that finds it (`dense`, `hybrid`, fusion weights) |
| `retriever.crowded`, `ranking.duplicates` | remove the near-duplicates (the audit lists them) |
| `ranking.reranker_demoted` | no reranker, or the measured one that keeps it |
| `ranking.not_rescued` | the measured reranker that lifts it, or a larger k |

Every blame carries an **evidence level**:

- **`confirmed`**: a configuration measured in this run that differs from the chosen pipeline *only in
  the blamed stage* hits this question. The fix names it with its result on this question.
- **`indicated`**: the probes point to the mechanism, but no configuration differing only in that stage
  was measured. The fix is labelled "not measured", with the command that would measure it.

`ragcourt explain [RUN]` prints, per miss: the question, its category, the quote and its place, the
cause (stage and mechanism) with its evidence and level, anything also seen, and the fix; then counts
per stage and mechanism, per category, with intervals. `--show ID` prints the quote's surroundings with the
chunk boundaries marked (§5.2). A legend explains each mechanism in one line (§13.2).

### 9.4 The probes

The extra measurements blame needs, all cheap and cached:

- **Quote alone**: the gold quote embedded with each embedder (one embedding per question per embedder),
  for `chunker.diluted` and `embedder.meaning`. Used only for diagnosis, never in a score.
- **Keyword rank**: BM25 over the same chunks for every question, whatever the retriever.
- **Every measured embedder's rank** of the hit, from the search (§10).
- **Ranks before and after the reranker**, and in each list of a hybrid retriever before fusion.
- **The quote's token position** in its chunk, measured only for chunks longer than the embedder's
  limit.
- **Near-duplicates** from the audit (`duplicate.near`) and the **twin passage** of `distractor`
  questions (§6.7).

### 9.5 Trusting the blame

Each mechanism has a planted case in the bundled corpus (with the fake embedder scripted to show it) and a
near miss that must not trigger it; the order of §9.1 is tested so a question never gets two causes. On a
real run, the share of `confirmed` blames is printed, so the user sees how much of the diagnosis rests on
measurement and how much on probes.

## 10. Search, cache, estimate and budget

### 10.1 Greedy search

Greedy by stage, embedders first (brief §6), on dev questions, by the chosen metric:

1. **Embedders:** each candidate embedder with the default chunker (`recursive:size=512,overlap=64`), the
   `dense` retriever and no reranker.
2. **Chunkers:** each candidate chunker (and its listed parameter values) with the best embedder.
3. **Retrievers:** `dense`, `bm25`, `hybrid` with the best chunker and embedder.
4. **Rerankers:** `none` and each candidate reranker on the best so far.

A stage's best is the top entry on dev by the overall score (the mean of the categories, §8.4); when
entries are tied (§8.4), the cheaper, then the higher on dev, then the smaller, then
the first listed is kept and the tie is reported (D-057). Candidates come from `ragcourt.toml` or flags; by
default every available built-in. Every evaluated configuration's held-out numbers appear in that stage's
leaderboard; the "best overall pipeline" is the last step's choice, reported on held-out questions.
When a category has a different winner from the overall one ("`bm25` leads on `exact_term`"), the output
says so with both intervals. Because each step varies one stage, the search also gives blame its
`confirmed` alternatives (§9.3).

### 10.2 The cache

Embeddings are cached in plain files, one folder per model under `.ragcourt/cache/embeddings/`, named
after the model identity (the endpoint's base URL and model name, or the local model's name and
digest). Each folder holds `model.json` (identity, dimension, cache version), `keys.txt` (one
`sha256(text)` per line) and `vectors.f32` (the vectors, float32, in the same order), both only ever
appended to. Loading reads the two files into a dictionary; a torn last write (a key without its vector)
is trimmed. A cached embedding is never sent again; a second identical run makes no embedding calls. A
layout change bumps the cache version and starts new folders. `ragcourt cache clear`
deletes the cache (D-016).

### 10.3 The plan, the estimate and the budget

Before any model call, `rank` prints **the plan** in plain words (D-030): each step in order; for each, the
role and the model that does it, where that choice came from (default, `ragcourt.toml`, flag), what the
model is shown and what it returns; the stages and candidates per search step; the number of chunks and
tokens to embed after the cache, the number of chat and judge calls, and an estimate of time and cost:
time from a calibration call (one small batch per endpoint, timed) or from the last run's timing; cost from
the configured prices, or `unknown`. `--budget-usd` and `--budget-minutes` stop the run before a step
that would exceed them: the steps done are reported, the step not run is named, and nothing is presented
as complete. A quick look (§6.8) says in the plan what it cannot tell and what the full run would still take.
Without `--yes`, the first run in a project, and any run estimated over one minute or over
$0, asks before starting; the plan is printed either way.

### 10.4 Progress and resume

A full run is long (writing about 540 questions, then the search), so it is never silent and never lost
(D-035):

- **Progress:** one line per step as it starts and ends, and while questions are written a line per
  category with asked, kept and dropped so far and the time left, from the measured pace. The same lines
  go to `runs/<run-id>/progress.jsonl`.
- **Resume:** every finished unit is written as it finishes: each question to `questions.jsonl`, each
  embedding to the cache, each evaluated configuration to `runs/<run-id>/`. `rank --resume` (or `rank`
  answering yes when it finds an unfinished run with the same plan) continues from there; a run whose plan
  changed (other documents, models or settings) starts afresh and says why.

## 11. Models

### 11.1 The one client

`io/client.py` is one client over the standard library (`urllib`) behind the `ModelClient` protocol in
`types`, with two dialects (D-007):

- **`ollama`** (the default; `http://localhost:11434`): chat with JSON output and thinking turned off,
  embeddings with their token counts (one text per call, `num_ctx` and `num_batch` set to the context
  length, D-041), `/api/show` for context lengths and sizes, `/api/ps` and `/api/tags`
  for what is loaded and installed, and `/api/pull` only from `setup`, after the user agrees.
- **`openai`**: any OpenAI-compatible endpoint (a hosted API, llama.cpp, vLLM, LM Studio): chat
  completions, embeddings, and the `/rerank` route of §7.3.

The in-process cross-encoders of the `local` extra implement the same protocol. Replies that should be
JSON are validated, and `<think>` blocks are removed before parsing. Retries: timeouts, 429 and 5xx only, three times with backoff; other
failures stop with `EndpointError` naming the endpoint, the status and what to check. Batches are sized
to the endpoint's limits and the model's input limit. Model loads are counted apart from calls in the
timing output, since the first call to an Ollama model includes loading it.

### 11.2 Privacy

Ollama on `localhost` is on the machine; with no configuration it is the only address ragcourt
contacts. Nothing leaves the machine unless the user configured an endpoint, and then only to that
endpoint: the
document windows for question generation and for `doctor`, the questions (alone, for the
answerable-without-documents check), the judge's prompts, chunk texts for embedding and reranking.
`audit` contacts nothing but the local Ollama, and only for token counts and limits. Keys are read from the environment variable the configuration names. No telemetry,
no update check. Logs never contain document text or keys. `docs/privacy.md` lists every call.

### 11.3 Setup

`ragcourt setup`, once per machine: checks that Ollama answers on `localhost` (or says how to install
and start it), reads the GPU memory and RAM Ollama reports, recommends models that fit from a small table
justified by measurement (D-027; on an 8 GB GPU: `gemma4` as question writer and judge,
`nomic-embed-text`, `embeddinggemma` and `mxbai-embed-large` as the first embedders to compare), shows their download
sizes, pulls the missing ones only after the user agrees, and runs the judge's self-test, shown case by
case (§6.6). It writes `ragcourt.toml` with the chosen model for each role, each line under a comment that
says what the role does and how to change it (§11.4), and the self-test result in the cache. Any Ollama
model can be named instead, at the prompt or later.

### 11.4 Roles and how to change them

Every model has a **role**: `writer` (writes questions and quotes), `judge` (§6.6), `embedders` (the
candidates of the search), `reranker` (the chat model of the `llm`
reranker) and `doctor` (§12). Changing one is one command or one line (D-031):

- `ragcourt models` shows each role: the model, where the choice came from, why it is the default,
  whether it is installed and its size, and for the judge its self-test score.
- `ragcourt models set judge qwen3:4b` (or `set embedders nomic-embed-text,bge-m3`) writes `ragcourt.toml`,
  keeping its comments; setting a judge runs its self-test at once and shows it.
- For one run: `--writer`, `--judge`, `--embedders`, `--reranker-model`.
- Precedence: a flag, then `ragcourt.toml`, then the built-in default; the plan (§10.3) prints which
  applied. An endpoint model is named `endpoint:<name>/<model>` after the endpoint is defined in
  `ragcourt.toml`.

## 12. Doctor

`ragcourt doctor <folder>`:

1. **Sample:** up to 8 documents (fixed seed, by size and type), each cut to about 4,000 characters.
2. **Describe:** the chat model returns JSON: the structure it sees (headings, tables, code, lists,
   boilerplate, average paragraph length) and up to three recommended built-in chunkers with parameters.
   Recommendations naming unknown stages or parameters are dropped and reported.
3. **Write (optional):** the model may return one chunker file, `def chunk(text: str) -> list[str]`,
   standard library only. It is saved to `.ragcourt/doctor/<sha256-prefix>.py`.
4. **Ask:** the code is printed in full with its SHA-256, and the user is asked to run it (`y/N`). It
   never runs without that answer, or `--approve <sha256>` matching exactly this file (D-017).
5. **Run isolated:** in a subprocess (`python -I`, a temporary working folder, an environment without
   keys or proxies), one document at a time on stdin, JSON out, with a timeout (10 s per document by
   default) and an output size limit. This is isolation from hangs and crashes, not a security sandbox:
   approval is the safety step, and the output says so.
6. **Validate:** a list of non-empty strings, each found in the source (§4.2); otherwise the chunker is
   rejected with the first failure shown.
7. **Measure:** the generated chunker and the recommendations join the chunker step of §10.1 with the
   baselines (the built-ins) on the same questions. It is reported better only when the paired interval
   says so on held-out questions; otherwise "no significant difference" or "worse" is printed with the
   numbers (brief §2).

## 13. Output and the command line

### 13.1 Commands

```text
ragcourt demo
ragcourt setup [--yes]
ragcourt models [set ROLE MODEL[,MODEL…]] [test judge] [--yes]
ragcourt prompts [show NAME]
ragcourt audit <folder> [--chunker SPEC]… [--embedder NAME] [--show DOC] [--json] [--fail-on CODE…]
ragcourt questions <folder> [--questions N] [--questions-file FILE] [--writer MODEL] [--judge MODEL]
ragcourt questions show [--dropped] [--reason TEXT]
ragcourt rank <folder> [--resume] [--quick | --questions N] [--questions-file FILE] [--writer MODEL] [--judge MODEL]
              [--metric NAME] [--k N] [--embedders LIST] [--chunkers SPECS] [--retrievers LIST] [--rerankers LIST]
              [--pipeline NAME [--no-search]]
              [--budget-minutes M] [--budget-usd X] [--yes] [--html]
ragcourt explain [RUN] [--show QUESTION-ID]
ragcourt report [RUN]
ragcourt doctor <folder> [--approve SHA256] [--no-code] [--timeout S] [--questions N] [--embedder NAME]
ragcourt cache clear
```

Common: `--workdir`, `--config`, `--stages DIR`, `--seed`, `--json`, `-q`. Exit codes: 0 done, 1 error, 2
usage, 3 a `--fail-on` check fired, 4 stopped by the budget, 130 interrupted (`--resume` continues).
`docs/cli.md` describes each.

`ragcourt demo` (change 0003) shows what ragcourt finds with no model and no network: the audit of the
bundled corpus by two chunkers, computed now with estimated sizes (the local Ollama is not contacted
either); then the boards, the summary and three misses of a real `rank` on that corpus, recorded once with
the default local models and shipped in the package (`ragcourt/demo/results.json`, with `recording.json`
saying the date, the machine, the command and why). The line naming the recording comes before any
recorded number; every recorded number is printed by the functions `rank` and `explain` use. It writes one
file, `.ragcourt/demo/report.html`. The recording is made again when the results format, the bundled
corpus or a default model changes.

### 13.2 Terminal output

Plain text tables, no colour when not a terminal, every number with its interval and its label
(measured, estimated, unknown). Every leaderboard and every blame list ends with a short legend of the
words it uses (hit, ceiling, each stage and mechanism, `confirmed` and `indicated`, "no significant
difference") and the rule
behind each, unless `-q`; `--help` of each command says what it will call and what it sends (D-030).

### 13.3 The results file

`.ragcourt/runs/<run-id>/results.json`, `format_version "1"`: the run's settings and seed, the
corpus and question-set hashes, the plan and the estimate, every evaluated configuration with its
metrics (mean and interval, dev and held-out), per-question ranks for held-out questions, the ties, the
chosen pipeline, ceilings, blame per miss with its evidence and fix, the actual time and cost. `explain`
and the HTML report read only this file.

### 13.4 The HTML report

`rank --html` (and `ragcourt report [RUN]`) writes one self-contained `report.html` from the results file:
the leaderboard per stage with interval bars and ties marked, the chosen pipeline and its ceilings, the
misses grouped by cause, each opening to the quote shown on its source text with the chunk boundaries,
and the audit summary of the chosen chunker. Standard library templating, inline CSS, a few lines of
inline JavaScript for filtering, no network requests when opened (D-019).

## 14. Errors and determinism

Errors are `RagCourtError` subclasses: `ConfigError`, `ExtraMissing`, `ChunkNotInSource`,
`EndpointError` (retryable or not), `BudgetExceeded`, `FormatVersionError`, `GeneratedCodeRejected`.
Every message says what happened and what to do. With the same documents, questions, seed and stages, a
run gives the same results file except for timings and its run id.

## 15. Testing, docs and examples

### 15.1 Suites

The suites of CONTRIBUTING.md: unit, contract, integration and acceptance by default (offline,
deterministic), real models by hand (`real_model`).

### 15.2 The bundled corpus and the fakes

`src/ragcourt/testing/corpus/`, shipped with the package (`ragcourt.testing.corpus_path()`, one copy,
D-037): thirteen short documents about a made-up job queue, written for the tests, in Markdown, plain
text, reStructuredText and HTML, each with cases on purpose (Markdown and HTML tables, fenced and
indented code, a running header and footer, a near-duplicate paragraph, a section longer than the fake
embedder's limit, setext headings, abbreviations, twin passages, rare terms, negations and numbers,
plain prose), and a hand-checked `questions.jsonl` beside it in `ragcourt.testing`. `FakeEmbedder`: deterministic vectors from
hashed word n-grams with a tokenizer and a limit, so similar texts are close and results are stable.
`ScriptedModel`: returns scripted replies per request in order and records what it was sent, for
question generation, the closed-book answer, the judge (including its self-test) and doctor. A fake
Ollama server on a free port (integration tests) answers the `ollama` dialect's routes.

### 15.3 Examples

One file per concept, in reading order, run by `tests/e2e/`: `quickstart.py` (audit a folder),
`boundaries.py` (see the cuts), `own_chunker.py` (a stage in one file), `own_pipeline.py` (the system you
already have, scored and blamed), `questions.py` (gold quotes,
drops, splits), `rank.py` (a leaderboard with intervals and ties), `budget_recall.py` (why size cannot
win), `blame.py` (one miss per cause), `cache_and_budget.py`, `judge.py` (what the judge is asked and shown, its self-test, its verdicts),
`models.py` (changing a role), `report.py`, `doctor.py`.

### 15.4 Docs

The pages of [`docs/README.md`](../docs/README.md), with every Python block run by the tests. `docs/one-question.md`
follows one question from its document through generation, validation, the split, chunking, retrieval
and reranking to its blame and fix, with real output from the bundled corpus.

## 16. Guarantees (acceptance cases)

Each is a test `tests/e2e/test_ac<N>_<slug>.py` through the public API or CLI that fails if the feature
is removed, except guarantee 26, which needs real models and is a marked test in `tests/real/`.

1. **Audit needs no key and no chat model.** `ragcourt audit` on the bundled corpus reports every check
   of §5.1 on the document planted for it; with sockets blocked (no Ollama) it still runs, with sizes
   labelled estimated.
2. **Checks are precise.** Each check fires on its planted case and not on its planted near miss (a
   sentence ending in an abbreviation, a heading repeated in the chunk, a table kept whole).
3. **Offsets are found by code.** Overlapping chunks, repeated text and whitespace-changed chunks map to
   the right spans; a chunk not in the source fails with `ChunkNotInSource` naming the chunk.
4. **Sizes are labelled.** Sizes and `size.over_limit` from the embedder's tokenizer say `measured`; with
   the tokenizer unavailable they say `estimated`, everywhere they appear.
5. **Gold is verbatim.** A generated quote not found in its document drops the question, and the drop is
   counted by reason in the question file and the output.
6. **Gold is independent of chunking.** The same question file scores every pipeline; changing the
   chunker changes no question, quote or split.
7. **The judge filters, with its reasons.** A question the scripted answerer answers correctly without the
   documents is dropped on the judge's verdict; an `UNKNOWN` answer keeps the question with no judge call;
   an invalid question is dropped by the validity verdict; every verdict and reason is in the question
   file; a user's question is never dropped by the judge.
8. **User questions are accepted** with quote validation; an ambiguous or missing quote is rejected with
   its reason.
9. **Search on dev, report on held-out.** Changing only held-out results never changes the chosen
   pipeline; every leaderboard number is from held-out questions.
10. **Metrics are right.** Every metric of §8.3 equals its hand-worked value on a fixture.
11. **Size cannot win.** A chunker that returns each document whole has `recall_at_k` of 1 where its
    chunks fit, and does not lead on `recall_at_budget`.
12. **Ties are said.** When the paired interval of the top two contains 0, the output says "no significant
    difference" and names no winner; when it does not, it names the winner.
13. **Blame is code and complete.** Every held-out miss has exactly one cause (stage and mechanism) by the
    order of §9.1; each mechanism's planted case gives that mechanism and its near miss does not; ceilings
    are non-increasing and their gaps equal the counts per stage.
14. **Every miss has a fix and an evidence level.** A `confirmed` blame names a measured configuration
    that differs only in the blamed stage and hits the question; an `indicated` one says "not measured"
    and gives the command that would measure it.
15. **The cache works.** A second identical run makes zero embedding calls; changing one document embeds
    only its chunks.
16. **The estimate comes first and the budget holds.** The estimate is printed before the first model
    call; a budget below the estimate stops before the step that would exceed it, exit code 4, with the
    finished steps reported and nothing called complete.
17. **Greedy, embedders first.** The plan and the results show the four steps of §10.1 in order, and
    only the configurations they list are evaluated.
18. **A stage is one file.** A chunker in the user's `ragcourt_stages/` appears in `audit` and `rank`
    with no other change; a duplicate name fails naming both files.
19. **Nothing leaves without an endpoint.** With no configuration, no address but Ollama on `localhost`
    is contacted by any command; with an endpoint configured, only its host and the local Ollama are; no
    key appears in any file ragcourt writes or logs.
20. **Generated code is asked, isolated, validated and measured.** Doctor's chunker does not run when the
    answer is no or the hash differs; a hanging chunker is stopped by the timeout; an invalid output is
    rejected; a valid one is ranked with the baselines and called better only with a significant
    held-out difference.
21. **The default suite is deterministic.** Two runs on the bundled corpus give the same results file
    except for timings and the run id.
22. **The layers hold.** `scripts/check_layers.py` passes on the package and fails on each kind of
    forbidden import.
23. **The report is self-contained.** `report.html` opens with no network request and shows every
    leaderboard, interval, tie and miss of the results file.
24. **Examples and docs run.** Every example and every Python block in the docs runs; the walk-through of
    `docs/one-question.md` matches the bundled corpus's real output.
25. **The judge proves itself first.** A scripted judge that grades refusals as correct fails the
    self-test, is refused with its errors shown, and no question is filtered by it; one that passes is
    used, and its score appears in the output.
26. **A long run shows progress and resumes.** `rank` prints its progress (step, questions kept per
    category, time left) as it goes; a run killed mid-way and started again with `--resume` continues from
    the questions, embeddings and configurations already finished, and its results equal those of an
    uninterrupted run.
27. **Setup asks before pulling.** `setup` never downloads a model without the user's yes (or `--yes`), and
    shows each model's size first.
28. **The plan comes before any model call.** `rank` prints every step with its role, model, the source of
    that choice and what the model is shown, before the first model call; a run whose output lacks the
    plan fails the test.
29. **The judge is explained.** Before the first judge call the output names the judge, what it is asked
    and shown and what it never decides; `prompts show` prints the exact prompts used; the self-test is
    shown case by case; `questions show --dropped` gives every dropped question with the judge's reason; a
    replaced prompt is named with its hash and retested.
30. **Models are easy to change.** `models set judge M` changes the judge in `ragcourt.toml` (keeping its
    comments) and runs the self-test; a flag overrides it for one run; the plan shows which applied.
31. **Categories are real.** Every kept question passed its category's code check (and the judge where
    §6.7 says so); a question that fails it is dropped and counted, never kept under that category.
32. **Categories are reported apart.** Leaderboards, intervals, ties and blame counts are given per
    category and overall (the mean of categories); a category with fewer than 30 held-out questions is
    shown as too few to rank, with its count; the smallest difference each category can tell apart is
    printed.
33. **Blame uses its probes.** On the planted cases, `chunker.diluted` is told from `embedder.meaning` by
    the quote-alone probe, `embedder.exact_words` from `embedder.meaning` by the keyword rank, and
    `chunker.over_limit` by the quote's token position.

36. **The demo needs nothing.** With sockets blocked, `ragcourt demo` exits 0, contacts no address, prints
    the live audit, then the recorded boards and misses under a line naming the recording's date, models
    and machine, and writes a self-contained `report.html` and no other file.
37. **The demo is real output.** The recording loads as the current `format_version`; what `demo` prints
    for it is what `rank`'s boards and summary and `explain` print for the same file; the README's excerpt
    is found in that output.

Guarantees 34 and 35 are proposed in [changes/0002](changes/0002-established-packages.md).

38. **A quick look never names a winner.** `rank --quick` prints in its plan that it cannot name one and
    why, before any model call; every board of the run is indicative with no winner; the smallest
    difference per category is printed; the summary names the full run, which reuses its questions.
39. **PDF is read with the extra.** A text PDF in the folder is loaded as a document whose text holds its
    sentences; `audit` runs on it and names the extractor; a question's quote is found verbatim in it.
40. **A PDF that cannot be read is said, not guessed.** Without the extra, each PDF is listed as skipped
    with the install command; a PDF with no text, an encrypted one and a damaged one are each skipped with
    their reason, and the other documents are still loaded.
41. **Your pipeline is scored like any other.** A `@pipeline` in `ragcourt_stages/` that wraps a known
    built-in pipeline gets, with `--pipeline`, the same held-out metrics as that pipeline; with
    `--no-search` no embedding model is called; returned texts not found in the documents are counted
    under the board and score nothing; the plan names the pipeline before anything is called.
42. **Its misses are blamed as far as code can see.** Each held-out miss of the user's pipeline has one
    cause: a `chunker` mechanism only when its chunks are listed, else `retrieval.not_found` or a
    `ranking` mechanism; without its chunks a retrieval miss says to list them; a blame is `confirmed` only
    when a pipeline measured in the same run hits the question.

## 17. Implemented and planned

**Implemented** (milestone 1, all nine steps): everything in §1 to §16. Every guarantee of §16 has its test
in `tests/e2e/` (guarantee 26 also in `tests/real/`, run against Ollama with `gemma4` and
`nomic-embed-text`). Tried on real corpora ([history/0004](history/0004-real-data.md)); real runs on the
bundled corpus take about two minutes with eight questions per category. Changes
[0003](changes/0003-demo-and-readme.md) (`demo`), [0004](changes/0004-quick-look.md) (`rank --quick`),
[0005](changes/0005-pdf.md) (PDF) and [0006](changes/0006-your-own-pipeline.md) (your own pipeline) are
implemented, with guarantees 36 to 42.

**Planned** (after 0.1): converters for public datasets with quote gold (history/0005); multi-quote
questions.

## 18. Known limits (0.1)

Chunkers must return text found in the source (no added context or rewriting), and a chunk of your own
pipeline that is not text of the source, or is found in more than one place, cannot be scored; blame for
your own pipeline stops at `retrieval.not_found` (ragcourt cannot see its embedder or its search), and one
pipeline is questioned per run; text formats and PDFs with a text layer (no
scanned pages, no images; PDF text is what the extractor gives: columns may be read out of order, words
broken at line ends stay broken, and a header repeated on every page of one PDF is not caught by
`boilerplate.repeated`, which counts documents); one language's stop words and sentence rules (English) for the closed-book check and
`cut.mid_sentence`; exact in-memory search (fine to about 200k chunks); intervals are wide with few
held-out questions; the greedy search can miss a combination that only wins jointly; blame that is only
`indicated` rests on probes, not on a measured alternative; questions need one quote (no question that
needs two passages); a small corpus may not support every category; question
quality and the judge's verdicts are only as good as the local model (the self-test guards the judge, not
the writer); a full run on 160 pages of documentation took about 70 minutes on a GPU like the owner's (8 GB),
and would take much longer on CPU only. Measured on the bundled corpus with `gemma4`: `distractor` questions are the hardest to obtain (the
judge rightly drops many whose look-alike passage also answers them), and on a dozen documents dev and
held-out choices can disagree; the output says so. One question is written per offered passage. The
`chonkie.semantic` adapter is left out (it downloads its own model, D-054). The time budget is checked
before each step, not during one; the money budget covers endpoint embeddings only and is an upper
bound. The overall ceiling pools all held-out questions; the time estimate uses measured rates, not a
calibration call; an unreadable `llm` reranker reply keeps the retrieval order (D-056). A key may travel over plain
`http://` to a server you configure; a stale lock on Windows must be deleted by hand; Windows and macOS
are tested in CI only (D-057).
