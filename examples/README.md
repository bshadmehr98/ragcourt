# Examples

One small runnable example per idea, in reading order. Each runs offline in a temporary folder with
ragcourt's fakes (`ragcourt.testing`): a scripted writer and judge, a fake Ollama, the fake embedder. With
Ollama running, the same commands work on your documents with real models. `tests/e2e/test_examples.py`
runs every one.

| Example | Shows |
|---|---|
| [`quickstart.py`](quickstart.py) | audit a folder: no model, no network, sizes estimated |
| [`own_chunker.py`](own_chunker.py) | your own chunker in one file, next to the built-ins |
| [`boundaries.py`](boundaries.py) | a document with its chunk boundaries marked |
| [`questions.py`](questions.py) | questions with gold quotes, filtered by the judge, each drop with its reason |
| [`rank.py`](rank.py) | the greedy search: leaderboards with intervals, ties said, misses blamed |
| [`budget_recall.py`](budget_recall.py) | why size cannot win: recall within a token budget |
| [`blame.py`](blame.py) | one miss, three causes, told apart by the probes |
| [`cache_and_budget.py`](cache_and_budget.py) | a second run embeds nothing; a budget stops a run before it starts |
| [`judge.py`](judge.py) | the judge's self-test, and a judge refused for grading refusals as correct |
| [`models.py`](models.py) | see and change the model of each role |
| [`report.py`](report.py) | the self-contained HTML report |
| [`doctor.py`](doctor.py) | a model-written chunker: shown, approved by hash, isolated, validated, measured |
