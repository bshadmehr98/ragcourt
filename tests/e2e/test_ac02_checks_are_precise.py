"""Guarantee 2: each check fires on its planted case and not on its near miss (design §5.1, §16).

The near misses: a sentence ending in an abbreviation, a heading repeated in the chunk, a table kept whole.
Through ``ragcourt audit`` with a user's chunker that cuts exactly where the test says.
"""

import json
from pathlib import Path

from tests.conftest import Run, audit_findings

CUTTER = """
from ragcourt.stages import chunker


@chunker("cut_at_marks")
def cut_at_marks(text: str) -> list[str]:
    return [piece for piece in text.split("@@") if piece.strip()]
"""


def audit_of(project: Path, corpus: Path, run: Run, documents: dict[str, str]) -> set[tuple[str, str]]:
    for name, text in documents.items():
        (corpus / name).write_text(text)
    (project / "ragcourt_stages").mkdir(exist_ok=True)
    (project / "ragcourt_stages" / "cut.py").write_text(CUTTER)
    code, out, _ = run("audit", corpus, "--embedder", "fake", "--chunker", "cut_at_marks", "--json")
    assert code == 0
    data = json.loads(out)
    return {(f["code"], f["document"]) for f in audit_findings(data)}


def test_planted_cases_fire_and_near_misses_do_not(
    project: Path, tmp_path: Path, run: Run, registry: None
) -> None:
    corpus = tmp_path / "docs"
    corpus.mkdir()
    table = "| a | b |\n| - | - |\n| 1 | 2 |\n"
    found = audit_of(
        project,
        corpus,
        run,
        {
            "cut.md": "The worker stops the @@job when it times out.\n",
            "abbrev.md": "Jobs run in order, etc.@@ The next one starts.\n",
            "lost.md": "# Retries\n\nThe first part. @@The second part has no heading.\n",
            "kept.md": "# Retries\n\nThe first part. @@Retries again: the heading is repeated.\n",
            "split.md": "Intro.\n\n| a | b | @@\n| - | - |\n| 1 | 2 |\n",
            "whole.md": "Intro.\n\n@@" + table,
        },
    )
    assert ("cut.mid_sentence", "cut.md") in found
    assert ("cut.mid_sentence", "abbrev.md") not in found
    assert ("context.no_heading", "lost.md") in found
    assert ("context.no_heading", "kept.md") not in found
    assert ("split.table", "split.md") in found
    assert ("split.table", "whole.md") not in found
