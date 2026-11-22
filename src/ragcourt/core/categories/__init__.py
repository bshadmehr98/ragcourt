"""Question categories, one file each, in the order questions are written (design §6.7, D-032).

Each file has ``NAME``, ``TESTS`` (the weakness it tests, in a few words), ``JUDGE`` (the prompt of the
judge's extra check, or None; with ``JUDGE_WANTS = False`` that check passes on a "no"), ``offers(index)``
(which passages may serve it) and ``check(question, quote, offer, index)`` (why a draft is not of the
category, or None). Adding a category is one file, its prompt ``writer.<name>.txt`` and its line below.
"""

from __future__ import annotations

from types import ModuleType

from ragcourt.core.categories import distractor, exact_term, keyword, negation, numeric, paraphrase

CATEGORIES: dict[str, ModuleType] = {
    module.NAME: module for module in (paraphrase, keyword, exact_term, distractor, negation, numeric)
}
USER = "user"
