# 0006: Measure and blame your own pipeline

## Status

`implemented in 0.1` (accepted by the maintainer 2026-11-24, proposed the same day; what building it changed is D-060). The owner's answers: a flag on `rank` with `--no-search`; chunks that are not text of the source are counted as unscorable; depth is always 50.

## Context

ragcourt ranks the stages it runs itself: its chunkers, embedders through its client, its in-memory
retrievers, its rerankers. A user's own stage can join each step in one file (§7.2). But most people who
would try ragcourt already have a retrieval system: a vector database, a framework's retriever, an index
they built months ago. For them a leaderboard of ragcourt's stages is advice by analogy; what they want to
know is how **their** system scores on these questions and why it misses. Vector databases are a non-goal
(§1), and stay one: ragcourt should not learn any database's API.

## Problem

Score and blame a retrieval system ragcourt did not build, through the smallest possible door, with the
same questions, metrics, intervals and honesty as its own pipelines.

## Options

1. **Leave it as it is:** the user re-creates their system from ragcourt's stages. Results apply only as
   far as the copy is faithful.
2. **Adapters for LangChain and LlamaIndex retrievers and for vector databases:** convenient, but it
   builds ragcourt on the tools it judges (the rule of 0002) and each adapter follows another project's
   API for ever.
3. **A fifth stage kind, `pipeline`: one function from a question to ranked chunk texts** (chosen). The
   user writes the few lines that call their own system; ragcourt needs to know nothing about it.

## Decision

### What the user writes

```python
# ragcourt_stages/mine.py
from ragcourt.stages import pipeline, pipeline_chunks

@pipeline("mine")
def mine(query: str, depth: int) -> list[str]:
    hits = my_index.search(query, limit=depth)      # your vector database, your framework
    return [hit.text for hit in hits]               # the chunk texts, best first


@pipeline_chunks("mine")                            # optional: every chunk your index holds
def mine_chunks() -> list[str]:
    return [row.text for row in my_index.scan()]
```

```text
ragcourt rank DOCS --pipeline mine              # the search, then yours against the best it found
ragcourt rank DOCS --pipeline mine --no-search  # only yours: needs no embedding model
```

### What ragcourt does

- **Finds the spans.** Each returned text is searched in the documents, exactly then
  whitespace-insensitively (§4.2), in every document. Found once: that span. Found in several places: the
  occurrence is unknown, so the text counts as a hit only if every place it could be holds the quote, and
  the count of such texts is reported. Not found (the system rewrote the chunk, or added a title or a
  summary): it cannot be scored; it keeps its rank, covers no tokens, and the board says "N of M returned
  chunks are not text of your documents". A pipeline whose every chunk is not found is refused with that
  message.
- **Scores it** on the same questions: every metric of §8.3 per held-out question, per category and
  overall, with intervals. Rank 1 to `depth` is what the function returned; the top k is its first k.
- **Shows it on a board** named `pipeline`, last. With the search: your pipelines and the search's chosen
  one, with the paired difference and "no significant difference" by the rule of §8.4. A user's pipeline
  is never chosen or tuned on dev: it is one fixed system, so only its held-out numbers are shown.
- **Blames its misses, as far as spans allow,** by the rules of §9.1 that need only spans and ranks:

  | Known | Blame |
  |---|---|
  | the chunks (`pipeline_chunks`) and no chunk holds the quote | `chunker.too_small`, `chunker.split` or `chunker.dropped`, as today |
  | a chunk holds the quote and it is not in the returned `depth` | stage `retrieval`, mechanism `retrieval.not_found`: ragcourt cannot see inside your system to tell the embedder from the search method, and says so |
  | it is returned below k | `ranking.distracted`, `ranking.duplicates` or `ranking.not_rescued`, as today |
  | no chunks were given and no returned text holds the quote | `retrieval.not_found`, with the note "give `pipeline_chunks` to tell a chunker's cut from a retrieval miss" |

  Evidence is `confirmed` when the search of the same run measured a pipeline that hits the question (it
  names it: "ragcourt's chosen pipeline finds it at rank 2"), else `indicated`. One probe is added when
  the chunks are known: BM25 over them, so a miss can say "keyword search over your own chunks finds it at
  rank 3". Still exactly one cause per miss.
- **Says what happens first.** The plan lists each pipeline: its name, its file, "called once per question
  with the question's text and depth 50; what it contacts is your code's business, not ragcourt's", and
  whether its chunks are known.

### Where it lives

`types/stages.py` gets the `Pipeline` alias; `stages/__init__.py` the fifth kind and its decorator;
`core/external.py` maps returned texts to spans; `flows/evaluate.py` gains the evaluation of a pipeline
(it reuses `core/metrics`); `core/blame/retrieval.py` holds the one new mechanism. A pipeline's result is
saved like any evaluation, so `--resume`, `explain` and the report work unchanged.

## Consequences

- The design's "four kinds" becomes "four kinds that ragcourt runs, and `pipeline`, a system it only
  questions": §2, §7.1, §7.2, §8.1, §9.1, §9.3, §10.1, §13.1 and §18 change; `docs/stages.md`,
  `docs/blame.md`, `docs/cli.md`, a tutorial chapter and an example (`examples/own_pipeline.py`, over an
  in-memory list standing in for a database).
- `results.json`: `PipelineSpec` gains an optional `pipeline` name; boards may hold the stage `pipeline`;
  blames may hold the stage `retrieval`. All additive: `format_version` stays "1".
- Not included, each its own record if wanted: chunks that are not text of the source (contextual
  chunking); evaluating generated answers; ready-made adapters for a framework or a database.

## Risks answered

- **Numbers are measured:** the same metrics, split, resamples and tie rule; an unscorable chunk is
  counted and shown, never treated as a miss in silence or a hit by guess.
- **Blame stays code:** spans and ranks only; one cause per miss; where code cannot tell (inside the
  user's system) the mechanism says "not found" and what would let it tell more, instead of guessing.
- **Gold independent of chunking:** the questions are written before and without the pipeline.
- **Layers:** the pipeline is a stage (layer 1) joined only in `flows`; `core/external.py` is pure.
- **Privacy:** ragcourt itself contacts nothing new. The user's function runs in-process like any stage of
  theirs (D-018) and may call their own services with the question text; the plan says so.
- **Nothing happens blindly:** the plan names each pipeline and what it is given.
- **Simplicity:** one more kind in the registry and one function for the user; no adapter, no dependency,
  no configuration beyond the flag.
- Files: additive keys only. Generated code: untouched (doctor writes chunkers, not pipelines).

## Acceptance cases (design §16)

41. **Your pipeline is scored like any other.** A `@pipeline` in `ragcourt_stages/` that wraps a known
    built-in pipeline gets, with `--pipeline`, the same held-out metrics as that pipeline; with
    `--no-search` no embedding model is called; returned texts not found in the documents are counted on
    the board and score nothing; the plan names the pipeline before anything is called.
42. **Its misses are blamed as far as code can see.** With its chunks given, a quote cut across two of them
    is `chunker.split`, a whole chunk not returned is `retrieval.not_found`, one returned below k is a
    `ranking` mechanism; without its chunks the miss is `retrieval.not_found` with the note; each miss has
    one cause, and it is `confirmed` only when a pipeline measured in the same run hits the question.

## Tests

`tests/e2e/test_ac41_your_pipeline_is_scored.py`, `test_ac42_your_pipeline_is_blamed.py`; unit tests for
the span mapping (found once, found twice, not found, whitespace changed) and the new mechanism with its
near miss; a contract test for the kind; the example and the docs blocks run in the tests.

## Migration and compatibility

Nothing existing changes: without `--pipeline` a run is as today.

## Open questions for the owner

1. **Flag or command:** `rank --pipeline` with `--no-search` (proposed), or a separate command
   (`ragcourt check DOCS --pipeline mine`)?
2. **Chunks that are not text of the source** (a title or summary added): counted as unscorable
   (proposed), or should the longest part found in the source be scored, as a follow-up record?
3. **Depth:** always 50 (proposed, as for every pipeline), or the function's own choice?
