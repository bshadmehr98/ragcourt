"""Your own chunker, in one file.

What: a chunker written by you, registered with a decorator, audited next to the built-ins.
How: a file in ``ragcourt_stages/`` with ``@chunker("name")``; every command finds it by name.
Why: a stage is one file (design §7.2); nothing else changes to measure your own idea.
"""

import tempfile
from pathlib import Path

from ragcourt.cli import main
from ragcourt.testing import corpus_path, offline_project

MY_CHUNKER = '''
from ragcourt.stages import chunker


@chunker("by_paragraph")
def by_paragraph(text: str, min_chars: int = 40) -> list[str]:
    """One chunk per paragraph; short ones are left out."""
    return [part for part in text.split("\\n\\n") if len(part.strip()) >= min_chars]
'''

with tempfile.TemporaryDirectory() as folder, offline_project(Path(folder)):
    (Path(folder) / "ragcourt_stages").mkdir()
    (Path(folder) / "ragcourt_stages" / "by_paragraph.py").write_text(MY_CHUNKER)
    chunkers = ["--chunker", "by_paragraph:min_chars=80", "--chunker", "recursive"]
    code = main(["audit", str(corpus_path()), *chunkers, "-q"])
assert code == 0
