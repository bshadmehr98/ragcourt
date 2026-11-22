"""Guarantee 22: the layers hold (design §3.1, §16).

``scripts/check_layers.py`` passes on the package and fails on each kind of forbidden import.
"""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "check_layers.py"


def check_layers(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root)], capture_output=True, text=True, check=False
    )


def test_the_package_passes() -> None:
    result = check_layers(ROOT / "src" / "ragcourt")
    assert result.returncode == 0, result.stdout
    assert "import layers: ok" in result.stdout


@pytest.mark.parametrize(
    ("module", "line", "why"),
    [
        ("types/documents.py", "from ragcourt.stages import chunker", "may not import stages"),
        ("core/metrics.py", "from ragcourt.io import config", "core (layer 2) may not import io"),
        ("io/config.py", "import ragcourt.core.metrics", "io (layer 2) may not import core"),
        (
            "stages/chunkers/fixed.py",
            "from ragcourt.stages.chunkers import sentence",
            "never imports another stage",
        ),
        ("commands/rank.py", "from ragcourt.commands import audit", "never imports another command"),
        ("commands/rank.py", "from ragcourt import cli", "nothing imports ragcourt.cli"),
        ("core/pipeline.py", "from ragcourt.testing import FakeEmbedder", "nothing imports ragcourt.testing"),
        ("__init__.py", "from ragcourt.commands import rank", "does not import ragcourt.commands"),
    ],
)
def test_each_kind_of_forbidden_import_fails(tmp_path: Path, module: str, line: str, why: str) -> None:
    path = tmp_path / "ragcourt" / module
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(line + "\n")
    result = check_layers(tmp_path / "ragcourt")
    assert result.returncode == 1
    assert why in result.stdout
