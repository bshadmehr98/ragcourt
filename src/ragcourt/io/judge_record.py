"""The judge's self-test results, kept per model and prompt version (design §6.6).

``.ragcourt/judge/<hash>.json`` holds every case with the judge's verdict and reason; the hash covers the
model and the prompts' hashes, so a changed prompt or another model runs the self-test again.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from ragcourt.types.questions import CaseResult, SelfTest


def record_path(workdir: Path, model: str, prompts: dict[str, str]) -> Path:
    """Where the self-test of ``model`` with these prompt hashes is kept."""
    key = json.dumps({"model": model, "prompts": prompts}, sort_keys=True)
    return workdir / "judge" / f"{hashlib.sha256(key.encode()).hexdigest()[:16]}.json"


def save_selftest(workdir: Path, test: SelfTest) -> None:
    """Keep a self-test's results."""
    path = record_path(workdir, test.model, test.prompts)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "model": test.model,
        "prompts": test.prompts,
        "results": [asdict(result) for result in test.results],
    }
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def load_selftest(workdir: Path, model: str, prompts: dict[str, str]) -> SelfTest | None:
    """The kept self-test of this model and these prompts, or None."""
    path = record_path(workdir, model, prompts)
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return SelfTest(model, prompts, [CaseResult(**item) for item in data["results"]])
