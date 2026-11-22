"""scripts/check_layers.py enforces the import layers of design/current.md §3.1."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "check_layers.py"


def check(tmp_path: Path, files: dict[str, str]) -> subprocess.CompletedProcess[str]:
    pkg = tmp_path / "ragcourt"
    for name, text in files.items():
        path = pkg / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(pkg)], capture_output=True, text=True, check=False
    )


def test_this_repository_keeps_its_layers() -> None:
    result = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize(
    ("files", "ok"),
    [
        ({"core/pipeline.py": "from ragcourt.types import Chunk\nfrom . import metrics\n"}, True),
        (
            {"stages/chunkers/a.py": "from ragcourt.stages import chunker\nfrom ragcourt.types import X\n"},
            True,
        ),
        ({"commands/rank.py": "from ragcourt.core import search\nfrom ragcourt.io import cache\n"}, True),
        ({"cli.py": "from ragcourt.commands import rank\n"}, True),
        ({"__init__.py": "from ragcourt.core.metrics import mrr\n"}, True),
        ({"types.py": "from ragcourt.core import metrics\n"}, False),
        ({"stages/chunkers/a.py": "from ragcourt.io.client import Client\n"}, False),
        ({"stages/chunkers/a.py": "from ragcourt.stages.chunkers.b import split\n"}, False),
        ({"stages/retrievers/dense.py": "from ..embedders import local\n"}, False),
        ({"core/pipeline.py": "from ragcourt.io import cache\n"}, False),
        ({"io/report.py": "import ragcourt.core.metrics\n"}, False),
        ({"commands/rank.py": "from ragcourt.commands.explain import explain\n"}, False),
        ({"commands/rank.py": "from ragcourt import cli\n"}, False),
        ({"core/blame.py": "from ragcourt.testing import fake\n"}, False),
        ({"__init__.py": "from ragcourt.commands import rank\n"}, False),
    ],
)
def test_rules(tmp_path: Path, files: dict[str, str], ok: bool) -> None:
    result = check(tmp_path, files)
    assert (result.returncode == 0) is ok, result.stdout
    if not ok:
        assert "imports ragcourt." in result.stdout
