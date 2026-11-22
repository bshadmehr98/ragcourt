# The judge

A judge is a chat model (by default the question writer, `gemma4`) that filters questions. Nothing it does
is hidden: before its first call in a run, ragcourt prints which model judges, why that one, what it is
asked and shown, and what it never decides.

**What it is asked**
- **Validity**: is this a real question (a short keyword search counts), and does the quote answer it on
  its own? "No" drops the question.
- **Answerable without the documents**: the writer first answers the question with no documents and is
  told to say `UNKNOWN` when it does not know. `UNKNOWN` keeps the question without a judge call. Any other
  answer goes to the judge with the quote: if the answer states the quote's fact, the question is too easy
  (a model knows it already) and is dropped.
- **Category** (for `negation`, `numeric` and `distractor`): is it really of its kind? For a distractor the
  judge is asked whether the other, similar passage also answers it; it must not.

**What it is shown**: the question, the quote, the closed-book answer and, for a distractor, the other
passage. **Never**: your chunks, scores or rankings. It never decides blame and never computes a metric.

**Its prompts** are plain files: `ragcourt prompts` lists them with their hashes; `ragcourt prompts show
judge.validity` prints one exactly. To replace one, put a file with the same name in a folder and set
`prompts_dir` in `ragcourt.toml`; every output then names your version by its hash, the judge's self-test
runs again on it, and the question set is written afresh.

**Its self-test.** Before its verdicts are used, a judge must agree with 40 labelled cases (right, wrong,
generic, refused and guessed answers; valid and invalid questions) at 90% or more. Below that it is refused,
its wrong cases are shown, and nothing is filtered by it. The result is kept per model and prompt version
and printed in every run. `gemma4` scored 98% on the owner's machine; smaller models tend to grade refusals
as correct, which the self-test catches.

```python
import tempfile
from pathlib import Path

from ragcourt.cli import main
from ragcourt.testing import ScriptedReplies, offline_project

# A judge that grades refusals as correct is refused.
with tempfile.TemporaryDirectory() as folder, offline_project(Path(folder), ScriptedReplies(lenient=True)):
    assert main(["models", "test", "judge", "-q"]) == 1
```

**Reading its verdicts**: every kept and dropped question keeps each verdict with its reason.
`ragcourt questions show` lists the kept ones; `--dropped` the dropped ones; `--reason TEXT` filters.
