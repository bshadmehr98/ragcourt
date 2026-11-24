"""The plan of a run, written for people before any model is called (design §10.3, D-030)."""

from __future__ import annotations

from typing import Any

from ragcourt.io.narration import ROLE_JOBS
from ragcourt.io.terminal import plural, section, table


def plan_text(plan: dict[str, Any], guess: Any) -> str:
    """The plan: each role, its model and where it came from, the steps and candidates, the estimate."""
    roles = [
        [role["role"], ", ".join(role["models"]), _source(role["source"]), *ROLE_JOBS[role["role"]]]
        for role in plan["roles"]
    ]
    steps = [["1. questions", _question_step(plan["questions"], guess.question_calls)], *_search_steps(plan)]
    if plan.get("pipeline"):
        steps.append([f"{len(steps) + 1}. your pipeline", _pipeline_step(plan["pipeline"], plan["settings"])])
    header = f"{plural(plan['documents'], 'document')}; metric {plan['metric']}; k = {plan['settings']['k']}."
    lines = [
        section("Plan"),
        header,
        "",
        table(["role", "model", "chosen by", "does", "is shown"], roles),
        "",
    ]
    lines.append(table(["step", "what"], steps))
    lines.append(
        f"\nAbout {plural(max(1, round(guess.minutes)), 'minute')}, estimated from measured speeds "
        "(less with a warm cache)."
    )
    if not plan.get("no_search"):
        calls = f"{guess.embed_texts} texts to embed and {guess.rerank_calls} reranking calls"
        lines.append(f"Up to {calls}. Local models cost nothing.")
    if plan.get("pipeline"):
        lines += ["", pipeline_note(plan["pipeline"])]
    if plan.get("quick"):
        lines += ["", quick_note(plan["quick"])]
    return "\n".join(lines)


def quick_note(quick: dict[str, Any]) -> str:
    """What a quick look can and cannot tell, and the way on to the full run."""
    return (
        f"A quick look: {quick['per_category']} questions per category. It shows where the misses are and "
        "which stages clearly fail.\nIt cannot name a winner: with so few held-out questions only large "
        "differences can be seen (each board says how large).\nThe full run reuses these questions, about "
        f"{quick['full_run_minutes']:.0f} minutes more (estimated): the same command without --quick."
    )


def _search_steps(plan: dict[str, Any]) -> list[list[str]]:
    candidates = plan["candidates"]
    if plan.get("no_search"):
        return []
    return [
        [
            "2. embedders",
            f"{', '.join(candidates['embedders'])}; {candidates['chunkers'][0]}, dense, no reranker",
        ],
        ["3. chunkers", f"{', '.join(candidates['chunkers'])}; the best embedder"],
        ["4. retrievers", f"{', '.join(candidates['retrievers'])}; the best chunker and embedder"],
        ["5. rerankers", f"none, {', '.join(candidates['rerankers'])}; the best so far"],
    ]


def _pipeline_step(pipeline: dict[str, Any], settings: dict[str, Any]) -> str:
    return (
        f"{pipeline['name']} ({pipeline['file']}): asked every question, depth {settings['depth']}; "
        "not in the estimate"
    )


def pipeline_note(pipeline: dict[str, Any]) -> str:
    """What happens to the user's own pipeline, said in the plan before it is called."""
    chunks = (
        "Its chunks are listed (pipeline_chunks), so a chunker's cut can be told from a retrieval miss."
        if pipeline["chunks_known"]
        else "Its chunks are not listed (no pipeline_chunks), so a miss cannot be traced to its chunker."
    )
    return (
        f"Your pipeline {pipeline['name']} is called once per question with the question's text; what it "
        f"contacts is your code's business, not ragcourt's.\n{chunks}\nIt is one fixed system: nothing in "
        "it is chosen or tuned; its held-out numbers are shown and its misses are blamed."
    )


def _question_step(questions: dict[str, Any], calls: int) -> str:
    if questions["reused"]:
        return f"reuse the {questions['total']} questions already written"
    if not questions["to_write"]:
        return f"use your {questions['total']} questions; none to write"
    return f"write up to {questions['to_write']} questions of {questions['total']}, about {calls} model calls"


def _source(source: str) -> str:
    return {"default": "built-in default", "flag": "command-line flag"}.get(source, source)
