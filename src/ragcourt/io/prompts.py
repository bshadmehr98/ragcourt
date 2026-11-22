"""The prompts every model is given, as readable files (design §6.6, D-030).

The bundled prompts live in ``ragcourt/prompts/``; a ``prompts_dir`` in ``ragcourt.toml`` may replace any of
them by file name. A prompt's identity is its name and the hash of its text, so a replaced prompt is named
in every output and the judge's self-test runs again on it. Placeholders are ``{{name}}``, filled by
``core.verdicts.fill``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ragcourt.errors import ConfigError

BUNDLED = Path(__file__).resolve().parent.parent / "prompts"


@dataclass(frozen=True)
class Prompt:
    """A prompt's name, text and hash, and whether the user replaced it."""

    name: str
    text: str
    replaced: bool = False

    @property
    def hash(self) -> str:
        """The first 12 hex digits of the text's SHA-256."""
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()[:12]


def prompt_names() -> list[str]:
    """Every bundled prompt's name."""
    return sorted(path.stem for path in BUNDLED.glob("*.txt"))


def load_prompt(name: str, prompts_dir: Path | None = None) -> Prompt:
    """The prompt ``name``: the user's file in ``prompts_dir`` if there is one, else the bundled one."""
    if prompts_dir is not None and (prompts_dir / f"{name}.txt").is_file():
        return Prompt(name, (prompts_dir / f"{name}.txt").read_text(encoding="utf-8"), replaced=True)
    path = BUNDLED / f"{name}.txt"
    if not path.is_file():
        raise ConfigError(f"No prompt named {name!r}; the prompts are {', '.join(prompt_names())}.")
    return Prompt(name, path.read_text(encoding="utf-8"))


def load_prompts(prompts_dir: Path | None = None) -> dict[str, Prompt]:
    """Every prompt by name."""
    return {name: load_prompt(name, prompts_dir) for name in prompt_names()}


def judge_cases() -> list[dict[str, Any]]:
    """The judge's labelled self-test cases (design §6.6)."""
    lines = (BUNDLED / "judge_cases.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]
