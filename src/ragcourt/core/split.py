"""Dev and held-out: choose on one third, report on two thirds (design §6.4, D-011)."""

from __future__ import annotations

import hashlib
from dataclasses import replace

from ragcourt.types.questions import Question

DEV = "dev"
HELD_OUT = "held-out"


def assign_splits(questions: list[Question], seed: int) -> list[Question]:
    """One third of each category ``dev``, the rest ``held-out``, by a hash of the id and the seed."""
    by_category: dict[str, list[Question]] = {}
    for question in questions:
        by_category.setdefault(question.category, []).append(question)
    splits: dict[str, str] = {}
    for members in by_category.values():
        ordered = sorted(members, key=lambda question: _rank(question.id, seed))
        dev_count = max(1, len(ordered) // 3) if len(ordered) >= 2 else 0  # every category can be chosen on
        for number, question in enumerate(ordered):
            splits[question.id] = DEV if number < dev_count else HELD_OUT
    return [replace(question, split=splits[question.id]) for question in questions]


def _rank(question_id: str, seed: int) -> str:
    return hashlib.sha256(f"{seed}:{question_id}".encode()).hexdigest()


def question_id(document: str, start: int, end: int, question: str) -> str:
    """A stable id: the same question on the same quote always gets it."""
    return hashlib.sha256(f"{document}:{start}:{end}:{question}".encode()).hexdigest()[:12]
