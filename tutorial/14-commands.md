# 14. Every command

| Command | What it does | Calls a model? |
|---|---|---|
| `ragcourt setup [--yes]` | once per machine: checks Ollama, recommends and pulls models, writes `ragcourt.toml`, tests the judge | Ollama, after your yes |
| `ragcourt models` | each role, its model, where the choice came from, installed or not, the judge's test | no |
| `ragcourt models set ROLE MODEL` | change a role's model in `ragcourt.toml` (comments kept); a new judge is tested at once | the judge's self-test |
| `ragcourt models test judge` | run the judge's self-test again, case by case | the judge |
| `ragcourt demo` | a live audit and a recorded real run of the bundled documents, in seconds | no, and no network |
| `ragcourt prompts` / `prompts show NAME` | list every prompt with its hash / print one exactly | no |
| `ragcourt audit FOLDER` | check how chunkers cut your documents (chapter 4) | the embedder, only to count tokens |
| `ragcourt questions FOLDER` | write, resume or reuse the question set (chapter 8) | writer and judge |
| `ragcourt questions show [--dropped] [--reason TEXT]` | read the kept or dropped questions and their verdicts | no |
| `ragcourt rank FOLDER` | the search, leaderboards and blame (chapter 12) | every role in the plan, printed first |
| `ragcourt explain [RUN] [--show ID]` | every miss of a finished run, or one in detail (chapter 13) | no |
| `ragcourt report [RUN]` | the run as one HTML file, no external links | no |
| `ragcourt doctor FOLDER` | a model suggests (and may write) a chunker, which is measured (chapter 17) | doctor, then the embedders |
| `ragcourt cache clear` | delete the cached embeddings | no |

`RUN` is a run id (a folder name in `.ragcourt/runs/`); the latest when left out.

## Flags of `rank`

| Flag | Means |
|---|---|
| `--embedders LIST`, `--chunkers SPECS`, `--retrievers LIST`, `--rerankers LIST` | what to compare (chunker specs separated by `;`) |
| `--metric NAME`, `--k N` | the metric to rank by (chapter 10), how many chunks count |
| `--questions N` | questions per kind (default 90) |
| `--quick` | a quick look: 20 questions per kind; shows the misses, names no winner; the full run reuses them |
| `--questions-file FILE` | add your own questions (below) |
| `--writer MODEL`, `--judge MODEL` | a different model for this run only |
| `--budget-minutes M`, `--budget-usd X` | stop before going over (chapter 18) |
| `--resume` | continue a stopped run |
| `--yes` | start without asking |
| `--html` | also write `report.html` |

`questions` takes `--questions`, `--questions-file`, `--writer` and `--judge` too. `audit` takes
`--chunker SPEC` (repeatable), `--embedder NAME`, `--show DOC` and `--fail-on CHECK…`. `doctor` takes
`--approve SHA256`, `--no-code`, `--timeout S`, `--questions N` and `--embedder NAME`.

## Flags of every command

| Flag | Means |
|---|---|
| `--workdir DIR` | the folder ragcourt keeps its files in (default: `.ragcourt/` in the current folder) |
| `--config FILE` | another `ragcourt.toml` |
| `--stages DIR` | the folder of your own stages (chapter 16) |
| `--seed N` | the seed of every random choice |
| `-q` | fewer explanations: no legends under tables |

`audit` and `explain` also take `--json`: the result as JSON, for scripts.
| `--help` | what the command calls and what it sends |

## Your own questions

If you already know questions your users ask, add them:

```text
ragcourt rank my_docs/ --questions-file mine.jsonl
```

`mine.jsonl` has one JSON object per line:

```text
{"question": "How long is a job kept after it finishes?", "quote": "Finished jobs are kept for 7 days."}
{"question": "default port", "quote": "The dashboard listens on port 8080.", "document": "dashboard.md"}
```

The quote must be in your documents, exactly (spaces and line breaks may differ). Add `"document"` when it
appears in more than one file, and `"start"` (its character offset in that document) when it appears more
than once in the same file. A public dataset with gold character spans converts directly. Your questions are the kind `user`: never dropped by the judge, never
checked against memory, ranked in their own column. A quote that is not found, or found in two places
without a `document`, is dropped with the reason.

## Exit codes

| Code | Means |
|---|---|
| 0 | done |
| 1 | an error: one plain message, never a traceback |
| 2 | the command line was wrong |
| 3 | an audit check named by `--fail-on` fired |
| 4 | stopped by a budget (`--resume` continues) |
| 130 | interrupted with Ctrl-C (`--resume` continues) |

Next: [settings and models](15-settings-and-models.md).
