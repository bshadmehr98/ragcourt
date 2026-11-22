"""Guarantee 18: a stage is one file (design §7.2, §16).

A chunker in the user's ``ragcourt_stages/`` is found by name with no other change, and a duplicate name
fails naming both files. ``audit`` (step 2) and ``rank`` (step 5) extend this test when they exist.
"""

from pathlib import Path

import pytest

from ragcourt import ConfigError, load_config, stages

pytestmark = pytest.mark.usefixtures("registry")

BY_PARAGRAPH = """
from ragcourt.stages import chunker


@chunker("by_paragraph")
def by_paragraph(text: str, min_chars: int = 20) -> list[str]:
    return [part for part in text.split("\\n\\n") if len(part) >= min_chars]
"""


def project_with(tmp_path: Path, files: dict[str, str]) -> Path:
    folder = tmp_path / "ragcourt_stages"
    folder.mkdir()
    for name, code in files.items():
        (folder / name).write_text(code)
    return tmp_path


def test_a_chunker_in_the_users_folder_is_found_by_name(tmp_path: Path) -> None:
    project = project_with(tmp_path, {"by_paragraph.py": BY_PARAGRAPH})
    stages.load_folder(load_config(project).stages_dir)
    chunk = stages.find("chunker", "by_paragraph").function
    assert chunk("A first paragraph here.\n\nshort\n\nA second paragraph here.") == [
        "A first paragraph here.",
        "A second paragraph here.",
    ]


def test_a_duplicate_name_fails_naming_both_files(tmp_path: Path) -> None:
    project = project_with(tmp_path, {"a.py": BY_PARAGRAPH, "b.py": BY_PARAGRAPH})
    with pytest.raises(ConfigError) as caught:
        stages.load_folder(load_config(project).stages_dir)
    message = str(caught.value)
    assert "Two chunkers are named 'by_paragraph'" in message
    assert str(project / "ragcourt_stages" / "a.py") in message
    assert str(project / "ragcourt_stages" / "b.py") in message
