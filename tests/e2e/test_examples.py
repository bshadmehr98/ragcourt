"""Guarantee 24 (examples): every example runs, offline (design §15.3)."""

import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES = sorted((Path(__file__).resolve().parents[2] / "examples").glob("*.py"))


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda path: path.name)
def test_example_runs(example: Path, tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(example)], cwd=tmp_path, capture_output=True, text=True, timeout=300, check=False
    )
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-3000:]


def test_every_example_is_listed_and_explained() -> None:
    listing = (EXAMPLES[0].parent / "README.md").read_text()
    for example in EXAMPLES:
        assert f"({example.name})" in listing
        text = example.read_text()
        assert all(word in text for word in ("What:", "How:", "Why:"))
