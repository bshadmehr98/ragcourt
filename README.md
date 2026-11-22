# ragcourt

Rank chunkers, embedding models, retrievers and rerankers on **your own documents**, and
say which stage caused each miss.

**Status: designed, not built.** The first design waits for the owner:
[design/changes/0001-initial-design.md](design/changes/0001-initial-design.md). Start with
[design/README.md](design/README.md) for why, and [design/current.md](design/current.md) for how.

## What it will do

- **Local models, no key.** `ragcourt setup` finds Ollama, recommends models that fit your machine and
  pulls them when you say so; nothing leaves your machine.
- **`audit`**: chunk your documents and flag chunks cut mid-sentence,
  chunks without their heading, split tables and code blocks, repeated headers and footers,
  near-duplicates, tiny chunks and chunks longer than your embedding model accepts, with the boundaries
  shown on your text.
- **`rank`**: a leaderboard per stage and the best overall pipeline, measured on questions whose gold
  answers are exact quotes from your documents (filtered by a judge model that must pass a self-test
  first), with confidence intervals, and "no significant
  difference" when the top results are tied.
- **Questions by kind**: different wording, keywords, exact terms, misleading questions, negations and
  numbers, many of each, so you see which embedder fails on which kind, not one blurred average.
- **`explain`**: for every failed question, the stage and the mechanism that lost it (cut in half by the
  chunker, drowned in a long chunk, past the embedder's input limit, exact words the embedder blurred, a
  look-alike passage, demoted by the reranker, …), computed by code, with whether a measurement confirms
  it and what would fix it.
- **`doctor`**: a model reads samples of your documents, recommends chunkers and may write one; you see
  the code and approve it before it runs, isolated, and it is ranked against the baselines like any
  other.

Nothing happens blindly: before any model is called you see which model does what and what it is shown;
the judge's prompts, its test cases and every verdict's reason are yours to read; `ragcourt models set`
changes any model in one command. Any OpenAI-compatible endpoint works too, if you configure one. No
telemetry.

## Install and run

Not yet. When the design is accepted and built:

```text
uv tool install ragcourt
ragcourt setup          # once: checks Ollama, pulls models that fit, tests the judge
ragcourt audit docs/    # seconds: how your chunker cuts your text
ragcourt rank docs/     # the ranking: shows its plan and time first (15-25 min the first time), then progress
```

## How this is being built

Specified by a human; designed and built by AI against a written design and tests; every decision is
reviewed by a human. The design history is in [design/changes/](design/changes/) and
[design/decisions.md](design/decisions.md). Contributors: [CONTRIBUTING.md](CONTRIBUTING.md); AI coding
tools: [AGENTS.md](AGENTS.md).

## License

Apache-2.0. Copyright 2026 Bahman Shadmehr.
