"""Guarantee 25: the judge proves itself first (design §6.6, §16)."""

from pathlib import Path

from ragcourt.testing import ScriptedReplies
from tests.conftest import Run


def test_a_judge_that_grades_refusals_as_correct_is_refused(
    project: Path, corpus: Path, run: Run, scripted: ScriptedReplies
) -> None:
    scripted.lenient = True
    code, out, err = run("questions", corpus)
    assert code == 1
    assert "FAILED" in out and "refusal" in out  # the cases are shown
    assert "would not be trusted" in err and "refusal case judged yes/correct" in err
    assert not any(call.startswith("You write one") for call in scripted.calls)  # nothing filtered by it


def test_a_judge_that_passes_is_used_and_its_score_shown(
    project: Path, corpus: Path, run: Run, scripted: ScriptedReplies
) -> None:
    code, out, _ = run("questions", corpus)
    assert code == 0
    assert "Score 100% on 40 labelled cases (90% needed): passed." in out
    again = run("questions", corpus)[1]
    assert "Score 100%" in again and "| expected" not in again  # kept: shown as a score, not case by case
