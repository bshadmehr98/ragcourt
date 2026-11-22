"""scripts/check_simple.py enforces the "Keep it simple" rules of CONTRIBUTING.md that ruff does not."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "check_simple.py"


def check(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True, check=False
    )


def long_function(lines: int) -> str:
    body = "".join(f"    x{n} = {n}\n" for n in range(lines))
    return f'def f():\n    """Doc."""\n{body}'


def test_this_repository_is_simple() -> None:
    result = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize(
    ("code", "ok"),
    [
        ("names = [n.strip() for n in raw if n]\n", True),
        ("pairs = [(a, b) for a in x for b in y]\n", False),
        ("kept = [n for n in raw if n if n > 1]\n", False),
        ("grid = [[c for c in row] for row in rows]\n", False),
        ("size = 'big' if n > 9 else 'small'\n", True),
        ("size = 'big' if n > 9 else 'mid' if n > 3 else 'small'\n", False),
        ("if (n := len(x)) > 3:\n    pass\n", False),
        ("def f():\n    global X\n", False),
        ("value = eval('1')\n", False),
        ("import importlib\n", False),
        ("class Meta(type):\n    pass\nclass A(metaclass=Meta):\n    pass\n", False),
        (long_function(39), True),
        (long_function(41), False),
        ("def f(x):\n    if x:\n        for y in x:\n            while y:\n                break\n", True),
        (
            "def f(x):\n    if x:\n        for y in x:\n            while y:\n                if y:\n                    break\n",
            False,
        ),
        ("X = 1\n" * 250, True),
        ("X = 1\n" * 251, False),
    ],
)
def test_rules(tmp_path: Path, code: str, ok: bool) -> None:
    path = tmp_path / "sample.py"
    path.write_text(code)
    result = check(path)
    assert (result.returncode == 0) is ok, result.stdout


@pytest.mark.parametrize("name", ["utils", "helpers", "common", "manager", "base"])
def test_junk_drawer_names_are_refused(tmp_path: Path, name: str) -> None:
    path = tmp_path / f"{name}.py"
    path.write_text("X = 1\n")
    assert check(path).returncode == 1


def test_classes_in_src_subclass_only_protocols_and_enums(tmp_path: Path) -> None:
    # The rule applies under src/, so the sample is written inside this repository's tree.
    folder = ROOT / "src" / "ragcourt" / "_scratch_check_simple"
    folder.mkdir()
    try:
        bad = folder / "shapes.py"
        bad.write_text("class Shape:\n    pass\n\nclass Square(Shape):\n    pass\n")
        good = folder / "kinds.py"
        good.write_text(
            "from enum import StrEnum\nfrom typing import Protocol\n\n"
            "class Kind(StrEnum):\n    A = 'a'\n\nclass Embed(Protocol):\n    pass\n"
        )
        assert check(bad).returncode == 1
        assert check(good).returncode == 0
    finally:
        for path in folder.iterdir():
            path.unlink()
        folder.rmdir()
