"""A run's folder, ``.ragcourt/runs/<run-id>/`` (design §10.4, §13.3).

``plan.json`` (the plan and its hash), ``progress.jsonl`` (one line per step as it starts and ends),
``configs/<hash>.json`` (each evaluated pipeline, written as it finishes, so ``--resume`` skips it) and
``results.json`` (everything ``explain`` and the report read). Plain JSON files a user can open.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ragcourt.errors import ConfigError, FormatVersionError
from ragcourt.types.results import Costs, Evaluation, PipelineSpec, QuestionResult

FORMAT_VERSION = "1"
RESULTS = "results.json"


def plan_hash(plan: dict[str, Any]) -> str:
    """A hash of everything that decides a run's results: a resumed run must have the same.

    Whether the questions were still to write is left out: a run stopped while writing them resumes too.
    """
    decisive = {key: value for key, value in plan.items() if key != "questions"}
    return hashlib.sha256(json.dumps(decisive, sort_keys=True).encode()).hexdigest()[:16]


def new_run(workdir: Path, plan: dict[str, Any]) -> Path:
    """A fresh run folder with its plan."""
    run_id = time.strftime("%Y%m%d-%H%M%S")
    folder = workdir / "runs" / run_id
    suffix = 1
    while folder.exists():
        suffix += 1
        folder = workdir / "runs" / f"{run_id}-{suffix}"
    (folder / "configs").mkdir(parents=True)
    (folder / "plan.json").write_text(
        json.dumps({"hash": plan_hash(plan), "plan": plan}, indent=1) + "\n", encoding="utf-8"
    )
    return folder


def unfinished_run(workdir: Path, plan: dict[str, Any]) -> Path | None:
    """The latest run with the same plan and no results yet, if any."""
    wanted = plan_hash(plan)
    for folder in sorted((workdir / "runs").glob("*"), reverse=True):
        saved = folder / "plan.json"
        open_run = saved.is_file() and not (folder / RESULTS).exists()
        if open_run and json.loads(saved.read_text(encoding="utf-8")).get("hash") == wanted:
            return folder
    return None


def find_run(workdir: Path, run_id: str | None) -> Path:
    """The finished run named ``run_id`` (a folder name in ``runs/``), or the latest one."""
    if run_id is None:
        return latest_run(workdir)
    names = [folder.name for folder in sorted((workdir / "runs").glob("*")) if (folder / RESULTS).is_file()]
    if run_id not in names:
        known = ", ".join(names[-5:]) or "none yet"
        raise ConfigError(f"No finished run {run_id!r} in {workdir / 'runs'} (finished runs: {known}).")
    return workdir / "runs" / run_id


def latest_run(workdir: Path) -> Path:
    """The latest run that has results."""
    finished = [folder for folder in sorted((workdir / "runs").glob("*")) if (folder / RESULTS).is_file()]
    if not finished:
        raise ConfigError(f"No finished run in {workdir / 'runs'}: run `ragcourt rank DOCS` first.")
    return finished[-1]


def log_progress(folder: Path, event: dict[str, Any]) -> None:
    """Append one progress line."""
    with (folder / "progress.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"time": round(time.time(), 3), **event}) + "\n")


def config_path(folder: Path, spec: PipelineSpec) -> Path:
    """Where one pipeline's evaluation is kept."""
    return folder / "configs" / f"{hashlib.sha256(spec.label.encode()).hexdigest()[:16]}.json"


def save_evaluation(folder: Path, evaluation: Evaluation) -> None:
    """Keep a finished evaluation."""
    data = {"spec": asdict(evaluation.spec), "costs": asdict(evaluation.costs)}
    data["results"] = {key: asdict(result) for key, result in evaluation.results.items()}
    config_path(folder, evaluation.spec).write_text(json.dumps(data) + "\n", encoding="utf-8")


def load_evaluation(folder: Path, spec: PipelineSpec) -> Evaluation | None:
    """A kept evaluation, or None."""
    path = config_path(folder, spec)
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    results = {key: _result(value) for key, value in data["results"].items()}
    return Evaluation(PipelineSpec(**data["spec"]), results, Costs(**data["costs"]))


def _result(data: dict[str, Any]) -> QuestionResult:
    return QuestionResult(
        data["question"], tuple(data["retrieved"]), tuple(data["final"]), dict(data["metrics"])
    )


def write_results(folder: Path, results: dict[str, Any]) -> Path:
    """Write ``results.json``."""
    path = folder / RESULTS
    path.write_text(
        json.dumps({"format_version": FORMAT_VERSION, **results}, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def write_partial(folder: Path, partial: dict[str, Any]) -> Path:
    """Write ``partial.json``: the finished steps of a run the budget stopped; ``--resume`` continues it."""
    path = folder / "partial.json"
    path.write_text(json.dumps(partial, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def read_results(folder: Path) -> dict[str, Any]:
    """Read ``results.json``, refusing a newer format."""
    data: dict[str, Any] = json.loads((folder / RESULTS).read_text(encoding="utf-8"))
    if str(data.get("format_version")) != FORMAT_VERSION:
        raise FormatVersionError(
            f"{folder / RESULTS} has format_version {data.get('format_version')}; upgrade ragcourt."
        )
    return data
