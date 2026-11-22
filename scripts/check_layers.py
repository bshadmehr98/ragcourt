#!/usr/bin/env python3
"""Check the import layers of design/current.md §3.1; exit 1 and name every import that breaks them.

    types, errors  ->  stages  ->  core | io  ->  commands  ->  cli

A module imports only from layers below its own. core and io sit side by side and never import each
other. Within stages, an implementation (``stages/<kind>/<name>.py``) imports only the registry
(``ragcourt.stages`` itself), never another implementation: only the pipeline joins stages. A command
never imports another command. Nothing imports ``cli`` or ``testing``; the package root (the public API)
and ``testing`` may import anything except ``cli`` and ``commands``.

Usage: ``python scripts/check_layers.py [--root src/ragcourt]``.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

PACKAGE = "ragcourt"
LAYER = {"types": 0, "errors": 0, "stages": 1, "core": 2, "io": 2, "commands": 3, "cli": 4}
TOP = 5  # the package root (__init__, __main__) and testing


def unit_of(parts: tuple[str, ...]) -> str:
    """The top-level unit a dotted module path belongs to: ``core``, ``stages`` … or ``""`` for the root."""
    return parts[1] if len(parts) > 1 else ""


def layer_of(unit: str) -> int:
    return LAYER.get(unit, TOP)


def module_parts(path: Path, root: Path) -> tuple[str, ...]:
    rel = path.relative_to(root).with_suffix("")
    parts = (PACKAGE, *rel.parts)
    return parts[:-1] if parts[-1] == "__init__" else parts


def imported(tree: ast.Module, parts: tuple[str, ...], is_package: bool) -> list[tuple[int, tuple[str, ...]]]:
    """Every ``ragcourt`` module this file imports, with its line, relative imports resolved."""
    found: list[tuple[int, tuple[str, ...]]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [(node.lineno, tuple(a.name.split("."))) for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = tuple((node.module or "").split(".")) if node.module else ()
            if node.level:
                here = parts if is_package else parts[:-1]
                base = here[: len(here) - node.level + 1] + base
            found += [(node.lineno, (*base, a.name)) for a in node.names]
    return [(line, target) for line, target in found if target[0] == PACKAGE]


def problem(source: tuple[str, ...], target: tuple[str, ...]) -> str | None:
    """Why importing ``target`` from ``source`` breaks a rule, or None."""
    src, dst = unit_of(source), unit_of(target)
    if dst in ("cli", "testing") and src != dst:
        return f"nothing imports ragcourt.{dst}"
    if src == dst:
        return same_unit_problem(source, target)
    if src in ("", "testing"):
        return f"the public API does not import ragcourt.{dst}" if dst == "commands" else None
    if layer_of(dst) >= layer_of(src):
        name = dst or "the package root"
        return f"{src} (layer {layer_of(src)}) may not import {name} (layer {layer_of(dst)})"
    return None


def same_unit_problem(source: tuple[str, ...], target: tuple[str, ...]) -> str | None:
    unit = unit_of(source)
    if unit == "stages" and len(source) > 3 and len(target) > 3 and source[:4] != target[:4]:
        return "a stage never imports another stage; only the pipeline joins them"
    if unit == "commands" and len(source) > 2 and len(target) > 2 and source[2] != target[2]:
        return "a command never imports another command"
    return None


def check(root: Path) -> list[str]:
    errors: list[str] = []
    for path in sorted(root.rglob("*.py")):
        parts = module_parts(path, root)
        tree = ast.parse(path.read_text(), filename=str(path))
        for line, target in imported(tree, parts, path.name == "__init__.py"):
            why = problem(parts, target)
            if why:
                errors.append(f"{path}:{line}: imports {'.'.join(target)}: {why}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check the import layers of design/current.md §3.1.")
    parser.add_argument("--root", type=Path, default=Path(__file__).parent.parent / "src" / PACKAGE)
    errors = check(parser.parse_args(argv).root)
    for error in errors:
        print(error)
    print(f"import layers: {len(errors)} problem(s)" if errors else "import layers: ok")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
