# 18. Files, privacy and safety

## What leaves your machine

Nothing, by default. The only address ragcourt contacts is Ollama on `localhost`. A model elsewhere is
used only when you configure an endpoint for it (chapter 15), and then only that address. There is no
telemetry. Models are downloaded only after you say yes. API keys are read from environment variables you
name, sent only in a request header, and never written to any file. Document text never goes to logs.

## The files ragcourt writes

Everything is a plain file in `.ragcourt/` in the folder you run it from (or in `--workdir DIR` instead). No database.

| Path | Holds |
|---|---|
| `questions.jsonl` | the question set: a header line, then one question per line with its quote, split and verdicts |
| `questions.dropped.jsonl` | every dropped question, with its reason |
| `cache/embeddings/<model>/` | the cached vectors (`model.json`, `keys.txt`, `vectors.f32`) |
| `cache/limits.json` | each model's measured input limit |
| `judge/<hash>.json` | the judge's self-test, per model and prompt version |
| `runs/<run-id>/plan.json` | what the run was going to do |
| `runs/<run-id>/progress.jsonl` | each finished step, for `--resume` |
| `runs/<run-id>/configs/*.json` | every measured pipeline, question by question |
| `runs/<run-id>/results.json` | the leaderboards, the chosen pipeline, every blame |
| `runs/<run-id>/report.html` | the report: one file, no scripts or links to fetch |
| `doctor/<hash>.py` | code a model wrote, kept for you to read |

These files contain your documents' text (questions and quotes). **Don't commit `.ragcourt/`** for
private documents; add it to `.gitignore`.

## Long runs

- **Resume**: Ctrl-C (exit 130) or a budget stop (exit 4) keeps every finished step. `ragcourt rank
  my_docs/ --resume` continues; nothing finished is measured twice. If the documents, models or settings
  changed since, no stopped run matches, and a new run starts, so results never mix.
- **Time budget**: `--budget-minutes 30` stops before a step that would go over, keeping what is done.
- **Money budget**: `--budget-usd 2` refuses a run whose estimated cost is over it.
- **Interrupted writes**: a crash in the middle of writing a file loses at most the last line; the cache
  and question files repair themselves on the next run.

## Clearing

```text
ragcourt cache clear       # the embeddings only
rm -r .ragcourt            # everything ragcourt wrote
```

Next: [real runs](19-real-runs.md).
