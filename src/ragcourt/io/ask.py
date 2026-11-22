"""Asking the user before anything that cannot be taken back (design §11.3, §12, D-017).

Without a terminal to answer from, the answer is no: nothing is downloaded or run on a guess.
"""

from __future__ import annotations

import sys


def read_answer(question: str) -> str:
    """The user's answer from the terminal, or "" when there is none."""
    if not sys.stdin.isatty():
        return ""
    try:
        return input(question)
    except EOFError:
        return ""


def confirm(question: str, *, yes: bool) -> bool:
    """True when ``--yes`` was given or the user answers y."""
    if yes:
        return True
    return read_answer(f"{question} [y/N] ").strip().lower() in ("y", "yes")
