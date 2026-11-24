"""Guarantees 36 and 37: the demo needs nothing, and shows real output (design §16, change 0003)."""

import json
import re
from pathlib import Path

from ragcourt.commands.demo import RECORDING
from ragcourt.io import run_files
from ragcourt.io.explain_output import misses_text
from ragcourt.io.rank_output import board_text, summary_text
from tests.conftest import Run

README = Path(__file__).resolve().parents[2] / "README.md"


def test_ac36_the_demo_needs_nothing(project: Path, run: Run, no_network: list[str]) -> None:
    code, out, err = run("demo")
    assert code == 0, err
    assert no_network == []  # not even the local Ollama is tried
    assert "1. Audit, computed now on the 13 bundled documents" in out and "cut.mid_sentence" in out
    recording = json.loads((RECORDING / "recording.json").read_text())
    line = next(line for line in out.splitlines() if line.startswith("Recorded on"))
    assert recording["date"] in line and recording["machine"] in line and "gemma4" in line
    assert out.index(line) < out.index("Leaderboard:")  # said before any recorded number
    assert "numbers of the bundled documents, not of yours" in out
    assert out.count("Leaderboard:") == 4 and "cause:" in out
    report = project / ".ragcourt" / "demo" / "report.html"
    assert str(report) in out
    page = report.read_text()
    assert "<h1>ragcourt run" in page
    assert not re.search(r"""(src|href)=["']https?://""", page)  # opens with no network request
    assert sorted(path.name for path in (project / ".ragcourt").rglob("*") if path.is_file()) == [
        "report.html"
    ]


def test_ac37_the_demo_prints_what_rank_and_explain_print_for_the_recording(project: Path, run: Run) -> None:
    results = run_files.read_results(RECORDING)  # refuses another format_version
    out = run("demo")[1]
    for board, step in zip(results["boards"], results["steps"], strict=True):
        assert board_text(board, step["chosen"]) in out
    assert summary_text(results, quiet=False) in out
    assert results["blames"] and "\n".join(misses_text(results["blames"][:3])) in out


def test_ac37_the_readme_excerpt_is_output_of_the_demo(project: Path, run: Run) -> None:
    out = run("demo")[1]
    block = README.read_text().split("<!-- demo-excerpt -->", maxsplit=1)[1].split("```")[1]
    lines = [line for line in block.splitlines()[1:] if line.strip()]
    assert len(lines) >= 8
    for line in lines:
        assert line in out, line
