"""Doctor: a model suggests chunkers and writes one; you approve it; everything is measured.

What: the model describes your documents and recommends built-in chunkers; it may write one. That code is
shown with its SHA-256 and runs only after you approve exactly that hash, in a separate process with a
timeout (not a sandbox); its output must be text of each document; it is then ranked with the baselines.
How: ``ragcourt doctor`` with a scripted doctor model, first without approval, then with ``--approve``.
Why: generated code is treated as untrusted until you have read it, and as unproven until measured.
"""

import tempfile
from pathlib import Path

from ragcourt.cli import main
from ragcourt.core.doctor import code_hash
from ragcourt.testing import ScriptedReplies, corpus_path, offline_project

ADVICE = '{"structure": {"headings": "Markdown"}, "recommendations": [{"chunker": "sentence:size=120"}]}'
CODE = "def chunk(text):\n    return [part for part in text.split('\\n\\n') if part.strip()]\n"


class Doctor(ScriptedReplies):
    """Scripted replies, plus the doctor's advice and code."""

    def __call__(self, prompt: str) -> str:
        if prompt.startswith("You advise on how to chunk"):
            return ADVICE
        if prompt.startswith("Write a Python chunker"):
            return CODE
        return super().__call__(prompt)


with tempfile.TemporaryDirectory() as folder, offline_project(Path(folder), Doctor()):
    assert main(["doctor", str(corpus_path()), "-q"]) == 0  # shown, not run: nobody approved it
    digest = next((Path(folder) / ".ragcourt" / "doctor").glob("*.py")).stem
    assert main(["doctor", str(corpus_path()), "--approve", code_hash(CODE), "-q"]) == 0
    assert digest == code_hash(CODE)[:16]
