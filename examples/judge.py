"""The judge proves itself first: its self-test, case by case.

What: a judge must agree with 40 labelled cases (90%) before its verdicts drop any question; a judge that
grades refusals as correct is refused, with its errors shown.
How: ``ragcourt models test judge`` with a good scripted judge, then with a lenient one.
Why: a small model as judge would otherwise keep questions it should drop, silently.
"""

import tempfile
from pathlib import Path

from ragcourt.cli import main
from ragcourt.testing import ScriptedReplies, offline_project

with tempfile.TemporaryDirectory() as folder, offline_project(Path(folder)):
    assert main(["models", "test", "judge", "-q"]) == 0
    assert main(["prompts", "show", "judge.closed_book"]) == 0
with tempfile.TemporaryDirectory() as folder, offline_project(Path(folder), ScriptedReplies(lenient=True)):
    assert main(["models", "test", "judge", "-q"]) == 1
