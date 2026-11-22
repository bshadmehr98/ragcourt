"""Doctor's pure parts: sampling documents, reading the model's advice and code, validating output (§12)."""

from __future__ import annotations

import hashlib
import inspect
import random
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast

from ragcourt import stages
from ragcourt.core.offsets import chunk_spans
from ragcourt.core.verdicts import json_object
from ragcourt.errors import ChunkNotInSource, ConfigError, GeneratedCodeRejected
from ragcourt.stages.specs import check_params, parse_spec
from ragcourt.types import Document

SAMPLE_DOCUMENTS = 8
SAMPLE_CHARS = 4000
FENCE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)


def sample(documents: Sequence[Document], seed: int) -> list[Document]:
    """Up to eight documents, spread over sizes and file types, each cut to about 4,000 characters."""
    ordered = sorted(documents, key=lambda item: (item.id.rsplit(".", 1)[-1], len(item.text), item.id))
    chosen = list(ordered)
    if len(chosen) > SAMPLE_DOCUMENTS:
        chosen = random.Random(seed).sample(ordered, SAMPLE_DOCUMENTS)  # noqa: S311 (a seeded sample)
    return [Document(item.id, item.text[:SAMPLE_CHARS]) for item in sorted(chosen, key=lambda item: item.id)]


def samples_text(documents: Sequence[Document]) -> str:
    """The samples as the model sees them."""
    return "\n\n".join(f"--- {document.id} ---\n{document.text}" for document in documents)


def chunker_menu() -> str:
    """The built-in chunkers with their parameters and defaults, for the model to choose from."""
    lines: list[str] = []
    for name in stages.names("chunker"):
        parameters = inspect.signature(stages.find("chunker", name).function).parameters.values()
        defaults = [f"{p.name}={p.default}" for p in parameters if p.default is not p.empty]
        lines.append(f"- {name}: {', '.join(defaults) or 'no parameters'}")
    return "\n".join(lines)


@dataclass(frozen=True)
class Advice:
    """The model's description of the documents, its usable recommendations, and those dropped."""

    structure: dict[str, str]
    recommended: list[tuple[str, str]]  # (spec, why)
    dropped: list[tuple[str, str]]  # (spec, reason)


def read_advice(reply: str) -> Advice:
    """Structure and recommendations; one naming an unknown stage or parameter is dropped with the reason."""
    data = json_object(reply) or {}
    structure = {str(key): str(value) for key, value in _mapping(data.get("structure")).items()}
    recommended: list[tuple[str, str]] = []
    dropped: list[tuple[str, str]] = []
    for item in _items(data.get("recommendations")):
        entry = _mapping(item)
        spec_text = str(entry.get("chunker", item if isinstance(item, str) else ""))
        problem = _spec_problem(spec_text)
        if problem:
            dropped.append((spec_text, problem))
        else:
            recommended.append((spec_text, str(entry.get("why", ""))))
    return Advice(structure, recommended[:3], dropped)


def _mapping(value: object) -> dict[str, object]:
    return cast(dict[str, object], value) if isinstance(value, dict) else {}


def _items(value: object) -> list[object]:
    return cast(list[object], value) if isinstance(value, list) else []


def _spec_problem(text: str) -> str | None:
    try:
        spec = parse_spec(text)
        check_params(stages.find("chunker", spec.name).function, spec)
    except ConfigError as error:
        return str(error)
    return None


def read_code(reply: str) -> str | None:
    """The chunker code in a reply (inside a fence or bare), or None when there is no ``def chunk``."""
    match = FENCE.search(reply)
    code = (match.group(1) if match else reply).strip() + "\n"
    return code if re.search(r"^def chunk\(", code, re.MULTILINE) else None


def code_hash(code: str) -> str:
    """The SHA-256 of the code, as the user approves it."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def validate(document: Document, output: object) -> list[str]:
    """The generated chunker's output for one document; ``GeneratedCodeRejected`` names the first failure."""
    items = _items(output)
    if not isinstance(output, list):
        raise GeneratedCodeRejected(f"On {document.id} it returned {type(output).__name__}, not a list.")
    pieces: list[str] = []
    for position, item in enumerate(items):
        if not isinstance(item, str) or not item.strip():
            raise GeneratedCodeRejected(f"On {document.id}, item {position} is not a non-empty string.")
        pieces.append(item)
    try:
        chunk_spans(document, pieces, "generated")
    except ChunkNotInSource as error:
        raise GeneratedCodeRejected(f"Its output is not text of the document: {error}") from error
    return pieces
