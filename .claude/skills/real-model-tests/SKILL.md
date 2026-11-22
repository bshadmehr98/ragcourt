---
name: real-model-tests
description: Run or write the marked tests that use a real model - a local embedding, chat or reranking model, or an OpenAI-compatible endpoint (tests/real, marker real_model) - and turn what they show into fixtures the default suite replays. Use before running or changing anything under tests/real, or when a model-backed stage, the model client, question generation or doctor changes.
---

# Real-model tests

Details: CONTRIBUTING.md, "Real-model tests". The default suite uses the fake embedder and the scripted
model; these tests use real ones.

**The models**
- By default the local Ollama on `localhost:11434` with the default models of `design/current.md` §11.3
  (run `ragdoctor setup` once, or `ollama pull` them). The first-minute test (guarantee 26) times
  `ragdoctor rank` on the bundled corpus and records the measured time; run it with nothing else using the
  GPU.
- Or an OpenAI-compatible endpoint chosen by environment variables: `RAGDOCTOR_TEST_BASE_URL`,
  `RAGDOCTOR_TEST_API_KEY` (empty for a local server), `RAGDOCTOR_TEST_EMBED_MODEL`,
  `RAGDOCTOR_TEST_CHAT_MODEL` and, for rerankers, `RAGDOCTOR_TEST_RERANK_MODEL`. A local server (Ollama,
  llama.cpp, vLLM, LM Studio) keeps the documents on the machine and costs nothing; prefer it.
- In-process local models need their extra installed (`uv sync --all-extras`); the first run downloads
  the model, so these tests are slow and marked `slow` too.
- Put the variables in `.claude/settings.local.json` or your shell, never in a committed file.

**Run**
- `uv run pytest -m real_model -q`. Tests skip with a precise reason when a variable, an extra or the
  endpoint is missing; a skip is never a pass, so say what was skipped.
- They run on the bundled corpus (`tests/fixtures/corpus/`) only, so a run costs a few cents at most on a
  paid endpoint; the test prints the estimate first.

**Record**
- When a real model shows a behaviour the default suite should keep (a question set it generated, a
  chunker doctor wrote, an endpoint's error reply), save it under `tests/fixtures/` and replay it with the
  scripted model. Check it by hand for anything private first (keys, hostnames, real documents).

**Write**
- Put the test in `tests/real/` with `@pytest.mark.real_model`.
- Assert what holds for any good model: generated quotes are found verbatim, the dropped count is stated,
  embeddings have the stated dimension, the cache makes a second run call nothing, a generated chunker is
  validated and measured. Never assert exact model text or exact scores.

**Report** what ran and what was skipped, with reasons, in the branch's summary (and the PR's "How it was
tested" once the repository is on GitHub).
