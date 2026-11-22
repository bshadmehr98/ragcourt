# 9. The judge

The **judge** is a chat model (by default the same `gemma4` that writes the questions) that filters
questions. It is the only place ragcourt trusts a model's opinion, so it is fenced in.

**What it is asked**
- *Validity*: is this a real question (a short keyword search counts), and does the quote answer it on its
  own?
- *Answerable from memory*: here is an answer written without your documents; does it state the quote's
  fact? If yes, the question is too easy and is dropped.
- *Category*, for negation, numeric and distractor questions: is it really of that kind? (For a
  distractor: does the other, similar passage also answer it? It must not.)

**What it is shown**: the question, the quote, the memory answer, and for a distractor the other passage.
**Never**: your chunks, any score, any ranking. It never decides why a question was missed and never
computes a number.

**Before a run**, ragcourt prints a paragraph saying which model judges, why that one, and all of the above.

## It must pass a test first

A small model as judge tends to accept refusals ("I don't know") as correct answers, which would keep
questions it should drop. So before its verdicts are used, the judge answers **40 labelled cases**: right,
wrong, generic, refused and guessed answers; valid and invalid questions. It must agree with 90% of them.
Below that, it is refused, its wrong cases are shown, and nothing is filtered by it.

```python
import tempfile
from pathlib import Path

from ragcourt.cli import main
from ragcourt.testing import ScriptedReplies, offline_project

# A good scripted judge passes; a "lenient" one that grades refusals as correct is refused (exit code 1).
with tempfile.TemporaryDirectory() as folder, offline_project(Path(folder)):
    assert main(["models", "test", "judge", "-q"]) == 0
with tempfile.TemporaryDirectory() as folder, offline_project(Path(folder), ScriptedReplies(lenient=True)):
    assert main(["models", "test", "judge", "-q"]) == 1
```

`gemma4` scored 98% on the owner's machine (it once disagreed on a keyword search, which is why the prompt
now says keyword searches are valid questions).

## Reading and changing its prompts

```text
ragcourt prompts                        # every prompt any model is given, with its hash
ragcourt prompts show judge.validity    # the exact text
ragcourt models test judge              # run the self-test again, case by case
```

To change a prompt, copy it into a folder, edit it, and set `prompts_dir` in `ragcourt.toml`. Every output
then names your version by its hash, the judge is tested again on it, and the questions are written afresh.

Next: [the metrics](10-metrics.md).
