"""Guarantee 20: generated code is asked, isolated, validated and measured (design §12, §16)."""

from pathlib import Path

import pytest

from ragcourt.testing import FakeOllamaState, ScriptedReplies
from tests.conftest import Run

GOOD = "def chunk(text):\n    return [part for part in text.split('\\n\\n') if part.strip()]\n"
HANGS = "import time\n\ndef chunk(text):\n    time.sleep(30)\n    return [text]\n"
INVENTS = "def chunk(text):\n    return ['Summary: ' + text[:20]]\n"
ADVICE = '{"structure": {"headings": "yes"}, "recommendations": [{"chunker": "sentence:size=100", "why": "short"}, {"chunker": "magic"}]}'


class Doctor(ScriptedReplies):
    """Scripted replies plus the doctor's two prompts."""

    def __init__(self, code: str) -> None:
        super().__init__()
        self.code = code

    def __call__(self, prompt: str) -> str:
        if prompt.startswith("You advise on how to chunk"):
            return ADVICE
        if prompt.startswith("Write a Python chunker"):
            return f"```python\n{self.code}```"
        return super().__call__(prompt)


def run_doctor(
    rank_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run, code: str, *args: str
) -> tuple[int, str, str]:
    _, state = rank_project
    state.reply = Doctor(code)
    return run("doctor", corpus, "--timeout", "2", *args)


def digest_in(out: str) -> str:
    return out.split("SHA-256: ")[1].split(maxsplit=1)[0]


def test_not_run_without_a_yes_or_with_another_hash(
    rank_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run
) -> None:
    code, out, _ = run_doctor(rank_project, corpus, run, GOOD)
    assert code == 0 and "Not run." in out and "not a sandbox" in out and GOOD.splitlines()[0] in out
    assert "dropped 'magic'" in out and "sentence:size=100:" in out
    assert "doctor-" not in out.split("Not run.")[1]
    code, out, _ = run_doctor(rank_project, corpus, run, GOOD, "--approve", "0" * 64)
    assert "Not run." in out


def test_a_hanging_or_inventing_chunker_is_rejected(
    rank_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run
) -> None:
    out = run_doctor(rank_project, corpus, run, HANGS)[1]
    out = run_doctor(rank_project, corpus, run, HANGS, "--approve", digest_in(out))[1]
    assert "Rejected: It ran longer than 2 s" in out
    out = run_doctor(rank_project, corpus, run, INVENTS)[1]
    out = run_doctor(rank_project, corpus, run, INVENTS, "--approve", digest_in(out))[1]
    assert "Rejected: Its output is not text of the document" in out


def test_an_approved_valid_chunker_is_measured_with_the_baselines(
    rank_project: tuple[Path, FakeOllamaState],
    corpus: Path,
    run: Run,
    registry: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("ragcourt.io.ask.read_answer", lambda question: "y")
    code, out, err = run_doctor(rank_project, corpus, run, GOOD)
    assert code == 0, err
    name = "doctor-" + digest_in(out)[:8]
    verdicts = [line for line in out.splitlines() if line.startswith(name)]
    assert len(verdicts) == 1
    assert any(
        word in verdicts[0] for word in ("no significant difference from", "better than", "worse than")
    )
    assert "the best baseline" in verdicts[0] and "[" in verdicts[0]
