# 18. Files, privacy and safety

## What leaves your machine

Nothing, by default. The only address ragcourt contacts is Ollama on `localhost`. A model elsewhere is
used only when you configure an endpoint for it (chapter 15), and then only that address. There is no
telemetry. Models are downloaded only after you say yes. API keys are read from environment variables you
name, sent only in a request header, never to an address a server redirects to, and never written to any
file. Use `https://` for a server that is not on your own machine or network. Document text never goes to
logs, and a link in your documents folder that points outside it (to a key file, say) is skipped.

## Run it from a folder you trust

Run ragcourt from a folder you trust. The documents can come from anywhere, but the folder you run
it *in* is your project: its `ragcourt.toml` chooses which servers are contacted and which environment
variable holds a key, and every `.py` file in its `ragcourt_stages/` runs as your own code, on every
command. Don't run ragcourt inside a folder you downloaded; run it beside it: `ragcourt audit
downloaded_docs/`.

## The files ragcourt writes

Everything is a plain file in `.ragcourt/` in the folder you run it from (or in `--workdir DIR` instead). No database.

| Path | Holds |
|---|---|
| `questions.jsonl` | the question set: a header line, then one question per line with its quote, split and verdicts |
| `questions.dropped.jsonl` | every dropped question, with its reason |
| `cache/embeddings/<model>-<hash>/` | the cached vectors (`model.json`, `keys.txt`, `vectors.f32`) |
| `cache/limits.json` | each model's measured input limit |
| `judge/<hash>.json` | the judge's self-test, per model and prompt version |
| `runs/<run-id>/plan.json` | what the run was going to do |
| `runs/<run-id>/progress.jsonl` | each finished step, for `--resume` |
| `runs/<run-id>/configs/*.json` | every measured pipeline, question by question |
| `runs/<run-id>/results.json` | the leaderboards, the chosen pipeline, every blame |
| `runs/<run-id>/report.html` | the report: one file that fetches nothing (a small inline script runs its filter buttons) |
| `lock` | while a command writes this folder, the id of its process: a second ragcourt here is refused |
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
