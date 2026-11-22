"""The audit: checks of chunks by code, one file per check, in the order they are reported (design §5.1).

Adding a check is one file with ``CODE``, ``MEANING`` and ``find(chunks, context)``, and its line below.
"""

from __future__ import annotations

from types import ModuleType

from ragcourt.core.audit import (
    boilerplate_repeated,
    cut_mid_sentence,
    duplicate_near,
    no_heading,
    size_over_limit,
    size_tiny,
    split_code,
    split_table,
)
from ragcourt.types.audit import AuditContext, Finding
from ragcourt.types.documents import Chunk

CHECKS: list[ModuleType] = [
    cut_mid_sentence,
    no_heading,
    split_table,
    split_code,
    boilerplate_repeated,
    duplicate_near,
    size_tiny,
    size_over_limit,
]
CODES = [check.CODE for check in CHECKS]
MEANINGS = {check.CODE: check.MEANING for check in CHECKS}


def audit(chunks: list[Chunk], context: AuditContext) -> list[Finding]:
    """Every finding of every check, check by check in the order of ``CHECKS``."""
    findings: list[Finding] = []
    for check in CHECKS:
        findings += check.find(chunks, context)
    return findings
