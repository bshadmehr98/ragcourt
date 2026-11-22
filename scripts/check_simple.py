#!/usr/bin/env python3
"""Check the "Keep it simple" rules of CONTRIBUTING.md that ruff does not; exit 1 and name every breach.

Checked on every Python file under src/, scripts/, tests/ and examples/:

- a module has at most 250 lines; a function at most 40 (its docstring not counted);
- blocks nest at most 3 deep inside a function (if, for, while, with, try, match);
- a comprehension has one ``for`` and at most one ``if``, and holds no other comprehension;
- no nested conditional expression (``a if b else c if d else e``) and no walrus (``:=``);
- no ``global``, ``nonlocal``, ``eval``, ``exec``, ``__import__``, ``globals()`` or ``locals()``;
- ``importlib`` only where the design loads the user's stages; no metaclasses;
- in src/, a class subclasses only ``Protocol``, an enum or ``HTMLParser``, except the errors in errors.py;
- no module named like a junk drawer (utils, helpers, misc, common, manager, base, …).

Usage: ``python scripts/check_simple.py [PATH …]`` (default: the four folders).
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FOLDERS = ("src", "scripts", "tests", "examples")
MAX_MODULE_LINES = 250
MAX_FUNCTION_LINES = 40
MAX_DEPTH = 3
BLOCKS = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Try, ast.Match)
COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
FORBIDDEN_CALLS = {"eval", "exec", "__import__", "globals", "locals"}
JUNK_NAMES = {"utils", "util", "helpers", "helper", "misc", "common", "manager", "managers", "handler"}
JUNK_NAMES |= {"handlers", "base", "stuff", "tools"}
# Protocols, enums, and the standard-library APIs that work only by subclassing (D-038).
ALLOWED_BASES = {
    "Protocol",
    "Enum",
    "StrEnum",
    "IntEnum",
    "HTMLParser",
    "BaseHTTPRequestHandler",
    "HTTPRedirectHandler",
}  # the last three: the standard library offers these hooks only as classes
IMPORTLIB_ALLOWED = {"src/ragcourt/stages/loader.py"}  # loading the user's stage folder (design §7.2)


def body_lines(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Lines of a function, without its docstring."""
    first = node.body[0]
    has_docstring = isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
    start = node.body[1].lineno if has_docstring and len(node.body) > 1 else node.lineno
    return (node.end_lineno or node.lineno) - start + 1


def is_elif(parent: ast.AST, child: ast.AST) -> bool:
    """True for the ``elif`` of an ``if``: the AST nests it in ``orelse``, but it reads as the same level."""
    return isinstance(parent, ast.If) and isinstance(child, ast.If) and parent.orelse == [child]


def max_depth(node: ast.AST, depth: int = 0) -> int:
    """The deepest block nesting below ``node``; a nested function starts again from zero."""
    deepest = depth
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue
        nests = isinstance(child, BLOCKS) and not is_elif(node, child)
        child_depth = depth + 1 if nests else depth
        deepest = max(deepest, max_depth(child, child_depth))
    return deepest


def comprehension_problem(node: ast.AST) -> str | None:
    if not isinstance(node, COMPREHENSIONS):
        return None
    if len(node.generators) > 1:
        return "a comprehension with more than one `for`: write a loop"
    if len(node.generators[0].ifs) > 1:
        return "a comprehension with more than one `if`: write a loop or name the condition"
    inner = [n for n in ast.walk(node) if isinstance(n, COMPREHENSIONS) and n is not node]
    if inner:
        return "a comprehension inside a comprehension: write a loop"
    return None


def expression_problem(node: ast.AST) -> str | None:
    if isinstance(node, ast.IfExp) and isinstance(node.orelse, ast.IfExp):
        return "a nested conditional expression: use if/elif"
    if isinstance(node, ast.NamedExpr):
        return "the walrus operator `:=`: assign on its own line"
    if isinstance(node, (ast.Global, ast.Nonlocal)):
        return "`global` or `nonlocal`: pass values in and return them"
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
        return f"`{node.func.id}()`: not allowed"
    return comprehension_problem(node)


def import_problem(node: ast.AST, rel: str) -> str | None:
    names: list[str] = []
    if isinstance(node, ast.Import):
        names = [alias.name for alias in node.names]
    elif isinstance(node, ast.ImportFrom):
        names = [node.module or ""]
    # importlib.metadata and importlib.resources read package data; they do not import code by name.
    uses_importlib = any(name in ("importlib", "importlib.util", "importlib.machinery") for name in names)
    if isinstance(node, ast.ImportFrom) and node.module == "importlib.util":
        uses_importlib = any(
            alias.name != "find_spec" for alias in node.names
        )  # asking whether a package exists
    if uses_importlib and rel not in IMPORTLIB_ALLOWED:
        return "`importlib`: only the stage loader imports code by name"
    return None


def class_problem(node: ast.AST, rel: str) -> str | None:
    if not isinstance(node, ast.ClassDef):
        return None
    if any(keyword.arg == "metaclass" for keyword in node.keywords):
        return "a metaclass: not allowed"
    if "src/ragcourt/" not in rel or rel.endswith("/errors.py"):
        return None
    for base in node.bases:
        name = base.attr if isinstance(base, ast.Attribute) else getattr(base, "id", "")
        if name not in ALLOWED_BASES:
            return f"class `{node.name}` subclasses `{name}`: use a function, a dataclass or a Protocol"
    return None


def function_problems(node: ast.AST) -> list[str]:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return []
    found: list[str] = []
    if body_lines(node) > MAX_FUNCTION_LINES:
        found.append(f"function `{node.name}` has {body_lines(node)} lines (at most {MAX_FUNCTION_LINES})")
    if max_depth(node) > MAX_DEPTH:
        found.append(f"function `{node.name}` nests blocks {max_depth(node)} deep (at most {MAX_DEPTH})")
    return found


def node_problems(node: ast.AST, rel: str) -> list[str]:
    found = function_problems(node)
    for problem in (expression_problem(node), import_problem(node, rel), class_problem(node, rel)):
        if problem:
            found.append(problem)
    return found


def check_file(path: Path) -> list[str]:
    rel = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.as_posix()
    text = path.read_text()
    errors: list[str] = []
    if path.stem in JUNK_NAMES:
        errors.append(f"{rel}: a module named `{path.stem}` says nothing; name it after what it does")
    lines = len(text.splitlines())
    if lines > MAX_MODULE_LINES:
        errors.append(f"{rel}: {lines} lines (at most {MAX_MODULE_LINES}); split it by concept")
    for node in ast.walk(ast.parse(text, filename=rel)):
        for problem in node_problems(node, rel):
            errors.append(f"{rel}:{getattr(node, 'lineno', 1)}: {problem}")
    return errors


def python_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(path.rglob("*.py")))
    return files


def main(argv: list[str]) -> int:
    paths = [Path(arg).resolve() for arg in argv] or [ROOT / folder for folder in FOLDERS]
    errors: list[str] = []
    for path in python_files(paths):
        errors.extend(check_file(path))
    for error in errors:
        print(error)
    print(f"simplicity: {len(errors)} problem(s)" if errors else "simplicity: ok")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
