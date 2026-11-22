# The command line

```text
ragcourt setup [--yes]
ragcourt models [set ROLE MODEL[,MODEL…]] [test judge] [--yes]
ragcourt prompts [show NAME]
ragcourt audit FOLDER [--chunker SPEC]… [--embedder NAME] [--show DOC] [--fail-on CODE…]
ragcourt questions FOLDER [--questions N] [--questions-file FILE] [--writer MODEL] [--judge MODEL]
ragcourt questions show [--dropped] [--reason TEXT]
ragcourt rank FOLDER [--resume] [--questions N] [--questions-file FILE] [--writer MODEL] [--judge MODEL]
                     [--metric NAME] [--k N] [--embedders LIST] [--chunkers SPECS] [--retrievers LIST]
                     [--rerankers LIST] [--budget-minutes M] [--budget-usd X] [--yes] [--html]
ragcourt explain [RUN] [--show QUESTION-ID]
ragcourt report [RUN]
ragcourt doctor FOLDER [--approve SHA256] [--no-code] [--timeout S] [--questions N] [--embedder NAME]
ragcourt cache clear
```

Every command also takes `--workdir DIR`, `--config FILE`, `--stages DIR`, `--seed N`, `--json` and `-q`
(no legend). `ragcourt COMMAND --help` says what the command calls and what it sends.

| Command | Calls a model? | What it does |
|---|---|---|
| `setup` | Ollama, to list and pull models (after your yes), and the judge's self-test | once per machine |
| `models` | only `models test judge` and `models set judge` | show or change the model of each role |
| `prompts` | no | list every prompt a model is given, print one exactly |
| `audit` | the embedder, only to count tokens | check chunks by code, no chat model |
| `questions` | the writer and the judge | write, reuse or resume the question set |
| `rank` | all roles in the plan, which it prints first | the greedy search, leaderboards, blame |
| `explain`, `report` | no | read a finished run's `results.json` |
| `doctor` | the doctor role, then the embedders | recommend, maybe write, and measure chunkers |
| `cache clear` | no | delete the cached embeddings |

Lists: `--embedders nomic-embed-text,bge-m3`; chunker specs carry their own commas, so they are separated
by `;`: `--chunkers "recursive:size=256,overlap=32;markdown"`.

**Exit codes**: 0 done, 1 an error (one message, never a traceback), 2 a usage error, 3 a check named by
`--fail-on` fired, 4 stopped by the budget, 130 interrupted (`rank --resume` continues).

**Files**, all plain and readable, in `.ragcourt/` of the current folder (or `--workdir`):

| Path | Holds |
|---|---|
| `questions.jsonl` | the question set: a header line, then one question per line with its quote, split and verdicts |
| `questions.dropped.jsonl` | every dropped question with its reason and verdicts |
| `cache/embeddings/<model>/` | `model.json`, `keys.txt`, `vectors.f32`: the embedding cache |
| `cache/limits.json` | each Ollama model's measured input limit |
| `judge/<hash>.json` | the judge's self-test, per model and prompt version |
| `runs/<run-id>/` | `plan.json`, `progress.jsonl`, `configs/*.json`, `results.json`, `report.html` |
| `doctor/<hash>.py` | code a model wrote, kept for you to read |

In CI, `ragcourt audit docs/ --fail-on split.table cut.mid_sentence` fails the build (exit 3) when those
checks fire.
