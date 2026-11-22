# ragdoctor

*(working name)* Rank chunkers, embedding models, retrievers and rerankers on **your own documents**, and
say which stage caused each miss.

**Status: designed, not built.** The first design waits for the owner:
[design/changes/0001-initial-design.md](design/changes/0001-initial-design.md). Start with
[design/README.md](design/README.md) for why, and [design/current.md](design/current.md) for how.

## What it will do

- **Local models, no key.** `ragdoctor setup` finds Ollama, recommends models that fit your machine and
  pulls them when you say so; after that a first ranking takes about a minute, and nothing leaves your
  machine.
- **`audit`**: chunk your documents and flag chunks cut mid-sentence,
  chunks without their heading, split tables and code blocks, repeated headers and footers,
  near-duplicates, tiny chunks and chunks longer than your embedding model accepts, with the boundaries
  shown on your text.
- **`rank`**: a leaderboard per stage and the best overall pipeline, measured on questions whose gold
  answers are exact quotes from your documents (filtered by a judge model that must pass a self-test
  first), with confidence intervals, and "no significant
  difference" when the top results are tied.
- **`explain`**: for every failed question, the one stage that lost it (the chunker, retrieval or
  ranking), computed by code, and what would fix it.
- **`doctor`**: a model reads samples of your documents, recommends chunkers and may write one; you see
  the code and approve it before it runs, isolated, and it is ranked against the baselines like any
  other.

Any OpenAI-compatible endpoint works too, if you configure one. No telemetry.

## Install and run

Not yet. When the design is accepted and built:

```text
uv tool install ragdoctor
ragdoctor setup          # once: checks Ollama, pulls models that fit, tests the judge
ragdoctor rank docs/     # the first ranking, in about a minute
```

## How this is being built

Specified by a human; designed and built by AI against a written design and tests; every decision is
reviewed by a human. The design history is in [design/changes/](design/changes/) and
[design/decisions.md](design/decisions.md). Contributors: [CONTRIBUTING.md](CONTRIBUTING.md); AI coding
tools: [AGENTS.md](AGENTS.md).

## License

Apache-2.0. Copyright 2026 Bahman Shadmehr.
