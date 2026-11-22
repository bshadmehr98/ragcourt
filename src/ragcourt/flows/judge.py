"""The judge's self-test before its verdicts are used, kept per model and prompt version (§6.6, D-026)."""

from __future__ import annotations

from collections.abc import Callable

from ragcourt.core.selftest import run_selftest
from ragcourt.errors import ConfigError
from ragcourt.io import question_file
from ragcourt.io.judge_record import load_selftest, save_selftest
from ragcourt.io.narration import failed_judge_text, selftest_text
from ragcourt.io.project import Project
from ragcourt.io.prompts import judge_cases, load_prompts
from ragcourt.types.questions import SelfTest

Say = Callable[[str], None]
JUDGE_PROMPTS = ("judge.validity", "judge.closed_book")


def check_judge(project: Project, model: str, templates: dict[str, str], say: Say) -> SelfTest:
    """The judge's self-test, from the record or run now and shown case by case; refused below 90%."""
    hashes = {name: question_file.text_hash(templates[name]) for name in JUDGE_PROMPTS}
    test = load_selftest(project.workdir, model, hashes)
    first_time = test is None
    if test is None:
        say(f"Running the judge's self-test ({len(judge_cases())} labelled cases) …")
        results = run_selftest(judge_cases(), templates, project.chat(model))
        test = SelfTest(model, hashes, results)
        save_selftest(project.workdir, test)
    say(selftest_text(test, cases=first_time or not test.passed))
    if not test.passed:
        raise ConfigError(failed_judge_text(test))
    return test


def judge_line(project: Project, model: str) -> str:
    """The judge's self-test score, as every run prints it (design §6.6)."""
    prompts = load_prompts(project.config.prompts_dir)
    test = load_selftest(project.workdir, model, {name: prompts[name].hash for name in JUDGE_PROMPTS})
    if test is None:
        return f"The judge {model} has no self-test on record."
    return selftest_text(test, cases=False).strip()
