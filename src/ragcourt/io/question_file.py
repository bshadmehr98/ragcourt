"""The question file, ``.ragcourt/questions.jsonl``, and its companion of dropped questions (design §6.5).

The first line is a header (format version, corpus hash, models, seed, settings, drop counts); then one
question per line. Questions are appended as they are written, so an interrupted run loses nothing
(design §10.4); the header is rewritten when the set is complete. Dropped questions, with every verdict and
reason, go to ``questions.dropped.jsonl`` for ``ragcourt questions show --dropped``.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ragcourt.errors import ConfigError, FormatVersionError
from ragcourt.types import Document
from ragcourt.types.questions import Dropped, Question, Span, Verdict

FORMAT_VERSION = "1"
QUESTIONS = "questions.jsonl"
DROPPED = "questions.dropped.jsonl"


def corpus_hash(documents: Sequence[Document]) -> str:
    """A hash of every document's id and text: questions are reused while it is unchanged."""
    digest = hashlib.sha256()
    for document in sorted(documents, key=lambda item: item.id):
        digest.update(document.id.encode() + b"\0" + document.text.encode() + b"\0")
    return digest.hexdigest()[:16]


def text_hash(text: str) -> str:
    """The first 12 hex digits of a text's SHA-256 (as a prompt's hash)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def question_data(question: Question) -> dict[str, Any]:
    """A question as one JSON line."""
    return asdict(question)


def question_from(data: dict[str, Any]) -> Question:
    """A question from one JSON line."""
    values: dict[str, Any] = dict(data)
    values["twin"] = Span(**data["twin"]) if data.get("twin") else None
    values["verdicts"] = tuple(Verdict(**item) for item in data.get("verdicts", []))
    return Question(**values)


def dropped_from(data: dict[str, Any]) -> Dropped:
    """A dropped question from one JSON line."""
    values: dict[str, Any] = dict(data)
    values["verdicts"] = tuple(Verdict(**item) for item in data.get("verdicts", []))
    return Dropped(**values)


def start_files(workdir: Path, header: dict[str, Any]) -> None:
    """Begin a new question set: a header line and an empty file of dropped questions."""
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / QUESTIONS).write_text(json.dumps({"format_version": FORMAT_VERSION, **header}) + "\n")
    (workdir / DROPPED).write_text("")


def append(workdir: Path, outcome: Question | Dropped) -> None:
    """Add one finished question or drop to its file."""
    name = QUESTIONS if isinstance(outcome, Question) else DROPPED
    with (workdir / name).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(outcome), ensure_ascii=False) + "\n")


def finish(workdir: Path, header: dict[str, Any], questions: list[Question]) -> None:
    """Rewrite the question file whole, with the final header and the splits."""
    lines = [json.dumps({"format_version": FORMAT_VERSION, **header})]
    lines += [json.dumps(question_data(question), ensure_ascii=False) for question in questions]
    (workdir / QUESTIONS).write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_questions(workdir: Path) -> tuple[dict[str, Any], list[Question], list[Dropped]] | None:
    """The header, questions and drops of the set in ``workdir``, or None when there is none."""
    path = workdir / QUESTIONS
    if not path.is_file():
        return None
    lines = json_lines(path)
    header: dict[str, Any] = lines[0] if lines else {}
    check_version(header, path)
    questions = [question_from(line) for line in lines[1:]]
    dropped_path = workdir / DROPPED
    dropped = [dropped_from(line) for line in json_lines(dropped_path)] if dropped_path.is_file() else []
    return header, questions, dropped


def json_lines(path: Path) -> list[dict[str, Any]]:
    """The JSON objects of a file written line by line; a last line cut short by a crash is left out."""
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    complete = lines if text.endswith("\n") else lines[:-1]
    found: list[dict[str, Any]] = []
    for number, line in enumerate(complete, start=1):
        if not line.strip():
            continue
        try:
            found.append(json.loads(line))
        except json.JSONDecodeError as error:
            raise ConfigError(
                f"{path} line {number} is damaged ({error.msg}); delete the file to start it again."
            ) from error
    return found


def check_version(header: dict[str, Any], path: Path) -> None:
    """Refuse a file written by a newer ragcourt."""
    version = str(header.get("format_version", FORMAT_VERSION))
    if version != FORMAT_VERSION:
        raise FormatVersionError(
            f"{path} has format_version {version}; this ragcourt reads {FORMAT_VERSION}. Upgrade ragcourt."
        )


def read_rows(path: Path) -> list[dict[str, Any]]:
    """The rows of a user's question file (JSON lines)."""
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ConfigError(f"{path} line {number} is not JSON: {error.msg}.") from error
    return rows
