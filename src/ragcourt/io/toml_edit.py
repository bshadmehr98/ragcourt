"""Changing one model role in ``ragcourt.toml`` while keeping every comment and other line (D-031)."""

from __future__ import annotations

import json
import re
from pathlib import Path

SECTION = re.compile(r"^\s*\[([^\]]+)\]\s*(#.*)?$")


def toml_value(models: tuple[str, ...], *, as_list: bool) -> str:
    """The TOML text of a role's value: a list for embedders, a string otherwise."""
    if as_list:
        return "[" + ", ".join(json.dumps(model) for model in models) + "]"
    return json.dumps(models[0])


def set_role(path: Path, role: str, value: str) -> None:
    """Write ``role = value`` in the ``[models]`` section, replacing the old line or adding one."""
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    section = ""
    for number, line in enumerate(lines):
        header = SECTION.match(line)
        section = header.group(1).strip() if header else section
        if section == "models" and re.match(rf"\s*{re.escape(role)}\s*=", line):
            lines[number] = f"{role} = {value}"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return
    lines = _insert(lines, f"{role} = {value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _insert(lines: list[str], entry: str) -> list[str]:
    """``entry`` added at the end of ``[models]``, which is created when missing."""
    start = next(
        (number for number, line in enumerate(lines) if SECTION.match(line) and "[models]" in line), None
    )
    if start is None:
        return [*lines, *([""] if lines else []), "[models]", entry]
    end = start + 1
    while end < len(lines) and not SECTION.match(lines[end]):
        end += 1
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1
    return [*lines[:end], entry, *lines[end:]]
