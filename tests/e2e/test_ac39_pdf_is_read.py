"""Guarantees 39 and 40: PDF is read with the extra; one that cannot be read is said (§16, change 0005)."""

import json
import sys
from pathlib import Path

import pytest

from ragcourt.testing import ScriptedReplies
from tests.conftest import Run
from tests.pdf_files import encrypted, pdf_bytes

QUOTE = "Larkspur keeps a dead job for 14 days before it deletes it."
PAGES = [
    ["Dead jobs", QUOTE, "A dead job can be retried by hand at any time."],
    ["Workers", "A worker sends a heartbeat every 5 seconds while it runs a job."],
]


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "manual.pdf").write_bytes(pdf_bytes(PAGES))
    (docs / "notes.md").write_text("# Notes\n\nQueues are drained in order of priority.\n")
    return docs


def test_ac39_a_pdf_is_a_document_audited_and_quoted_verbatim(
    project: Path, folder: Path, run: Run, scripted: ScriptedReplies, no_network: list[str]
) -> None:
    code, out, err = run("audit", folder, "--chunker", "sentence:size=30", "--show", "manual.pdf")
    assert code == 0, err
    assert "2 documents" in out
    assert "1 document from PDF, as text extracted by pypdf" in out
    assert QUOTE in out  # --show prints the text ragcourt was given


def test_ac39_a_quote_is_found_verbatim_in_a_pdf(
    project: Path, folder: Path, run: Run, scripted: ScriptedReplies, tmp_path: Path
) -> None:
    mine = tmp_path / "mine.jsonl"
    mine.write_text(json.dumps({"question": "How long is a dead job kept?", "quote": QUOTE}) + "\n")
    code, _, err = run("questions", folder, "--questions", "0", "--questions-file", mine)
    assert code == 0, err
    lines = (project / ".ragcourt" / "questions.jsonl").read_text().splitlines()[1:]
    kept = [json.loads(line) for line in lines]
    assert [(item["document"], item["quote"]) for item in kept] == [("manual.pdf", QUOTE)]


def test_ac40_a_pdf_that_cannot_be_read_is_skipped_with_its_reason(
    project: Path, folder: Path, run: Run, no_network: list[str]
) -> None:
    (folder / "scan.pdf").write_bytes(pdf_bytes([[]]))
    (folder / "locked.pdf").write_bytes(encrypted(pdf_bytes(PAGES)))
    (folder / "torn.pdf").write_bytes(pdf_bytes(PAGES)[:150])
    code, out, err = run("audit", folder, "--json")
    assert code == 0, err
    data = json.loads(out)
    assert data["documents"] == 2  # the good PDF and the Markdown file are still loaded
    reasons = {entry["path"]: entry["reason"] for entry in data["skipped"]}
    assert reasons["scan.pdf"].startswith("no text in this PDF")
    assert reasons["locked.pdf"].startswith("encrypted PDF")
    assert reasons["torn.pdf"].startswith("damaged or not a PDF")


def test_ac40_without_the_extra_each_pdf_is_listed_with_the_install_command(
    project: Path, folder: Path, run: Run, no_network: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(sys.modules, "pypdf", None)
    code, out, err = run("audit", folder, "--json")
    assert code == 0, err
    data = json.loads(out)
    assert data["documents"] == 1
    assert data["skipped"] == [{"path": "manual.pdf", "reason": "install 'ragcourt[pdf]' to read PDF"}]
