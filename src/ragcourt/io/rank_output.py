"""Writing a run for people: the plan, the leaderboards, ceilings, blame and the legend (design §13.2).

Everything is rendered from plain data (the contents of ``results.json``), so ``rank``, ``explain`` and
``report`` say the same thing.
"""

from __future__ import annotations

from typing import Any

from ragcourt.io.narration import ROLE_JOBS
from ragcourt.io.terminal import legend, section, table

LEGEND = {
    "hit": "a chunk whose span holds the whole gold quote",
    "held-out": "the two thirds of questions every number here comes from; dev questions chose",
    "[low, high]": "the 95% interval of the mean, from bootstrap resamples of the questions",
    "overall": "the mean of the category means: every category weighs the same",
    "no significant difference": "the paired interval of the top two contains 0: no winner is named",
    "= (tied)": "an entry the top cannot be told apart from",
    "too few to rank": "a category with fewer held-out questions than the minimum; not in the overall",
    "smallest difference": "half the width of the top two's paired interval: smaller gaps cannot be seen",
    "recall_at_budget": "share of the quote's tokens in the first 400 reference tokens retrieved",
    "ceilings": "chunker: an intact chunk exists; retrieval: it was retrieved; hit@k: it made the top k",
}


def plan_text(plan: dict[str, Any], guess: Any) -> str:
    """The plan: each role, its model and where it came from, the steps and candidates, the estimate."""
    roles = [
        [role["role"], ", ".join(role["models"]), _source(role["source"]), *ROLE_JOBS[role["role"]]]
        for role in plan["roles"]
    ]
    candidates = plan["candidates"]
    steps = [
        ["1. questions", _question_step(plan["questions"], guess.question_calls)],
        [
            "2. embedders",
            f"{', '.join(candidates['embedders'])}; {candidates['chunkers'][0]}, dense, no reranker",
        ],
        ["3. chunkers", f"{', '.join(candidates['chunkers'])}; the best embedder"],
        ["4. retrievers", f"{', '.join(candidates['retrievers'])}; the best chunker and embedder"],
        ["5. rerankers", f"none, {', '.join(candidates['rerankers'])}; the best so far"],
    ]
    header = f"{plan['documents']} documents; metric {plan['metric']}; k = {plan['settings']['k']}."
    lines = [
        section("Plan"),
        header,
        "",
        table(["role", "model", "chosen by", "does", "is shown"], roles),
        "",
    ]
    lines.append(table(["step", "what"], steps))
    lines.append(
        f"\nAbout {guess.minutes:.0f} minutes, estimated from measured speeds (less with a warm cache)."
    )
    calls = f"{guess.embed_texts} texts to embed and {guess.rerank_calls} reranking calls"
    lines.append(f"Up to {calls}. Local models cost nothing.")
    return "\n".join(lines)


def _question_step(questions: dict[str, Any], calls: int) -> str:
    if questions["reused"]:
        return f"reuse the {questions['total']} questions already written"
    if not questions["to_write"]:
        return f"use your {questions['total']} questions; none to write"
    return f"write up to {questions['to_write']} questions of {questions['total']}, about {calls} model calls"


def _source(source: str) -> str:
    return {"default": "built-in default", "flag": "command-line flag"}.get(source, source)


def _cell(value: dict[str, float]) -> str:
    return f"{value['mean']:.2f} [{value['low']:.2f}, {value['high']:.2f}]"


def board_text(board: dict[str, Any], chosen: str | None) -> str:
    """One leaderboard: overall and per category, ties marked, the winner or the tie said plainly."""
    categories = _categories(board)
    rows: list[list[object]] = []
    for row in board["rows"]:
        cells = [_cell(row["categories"][name]) if name in row["categories"] else "-" for name in categories]
        rows.append(["=" if row["tied_with_top"] else "", row["label"], _cell(row["overall"]), *cells])
    title = f"Leaderboard: {board['stage']}s ({board['metric']}, held-out)"
    lines = [section(title), table(["", "pipeline", "overall", *categories], rows), _verdict(board)]
    for name, count in sorted(board["too_few"].items()):
        lines.append(f"{name}: too few to rank ({count} held-out questions).")
    for name, label in sorted(board["category_leaders"].items()):
        lines.append(f"On {name}, {label} leads (separably).")
    if board["smallest_difference"]:
        gaps = ", ".join(
            f"{name} {value:.2f}" for name, value in sorted(board["smallest_difference"].items())
        )
        lines.append(f"Smallest difference these questions can tell apart: {gaps}.")
    if chosen is not None:
        lines.append(f"Chosen for the next step (on dev questions): {chosen}")
        lines += _disagreement(board, chosen)
    return "\n".join(lines)


def _disagreement(board: dict[str, Any], chosen: str) -> list[str]:
    """Said when the held-out winner is not the pipeline chosen on dev (D-057)."""
    winner = board["winner"]
    if not winner or chosen.startswith(winner):
        return []
    return [
        f"Note: on held-out questions {winner} is separably better than this choice; the dev questions "
        "could not tell them apart. Prefer the winner, or write more questions (--questions N)."
    ]


def _categories(board: dict[str, Any]) -> list[str]:
    names: set[str] = set()
    for row in board["rows"]:
        names |= set(row["categories"])
    return sorted(names)


def _verdict(board: dict[str, Any]) -> str:
    if board.get("indicative"):
        return (
            "Every category has too few held-out questions to rank: these numbers are indicative; no winner."
        )
    if board["winner"]:
        return f"Winner: {board['winner']}."
    tied = ", ".join(row["label"] for row in board["rows"] if row["tied_with_top"])
    return f"No significant difference between {board['rows'][0]['label']} and {tied}: no winner."


def summary_text(results: dict[str, Any], *, quiet: bool) -> str:
    """The end of a run: the chosen pipeline, its ceilings, the causes of its misses, and the legend."""
    rows = [_ceiling_row(name, value) for name, value in results["ceilings"].items()]
    lines = [section("Chosen pipeline"), results["chosen"], section("Ceilings (held-out)")]
    lines += [table(["group", "questions", "chunker", "retrieval", "hit@k"], rows), *causes_text(results)]
    share = results.get("confirmed_share")
    if share is not None:
        lines.append(f"\n{share:.0%} of blames are confirmed by a measured alternative; the rest by probes.")
    lines.append("Every miss, with its evidence and fix: `ragcourt explain`.")
    if not quiet:
        lines += ["", legend(LEGEND)]
    return "\n".join(lines) + "\n"


def _ceiling_row(name: str, value: dict[str, Any]) -> list[object]:
    levels = [f"{value[level]:.2f}" for level in ("chunker", "retrieval", "hit_at_k")]
    return [name, value["questions"], *levels]


def causes_text(results: dict[str, Any]) -> list[str]:
    """Counts of misses per mechanism and category."""
    counts: dict[tuple[str, str], int] = {}
    for blame in results["blames"]:
        key = (blame["mechanism"], blame["category"])
        counts[key] = counts.get(key, 0) + 1
    if not counts:
        return [section("Misses"), "No held-out question was missed."]
    rows = [[mechanism, category, count] for (mechanism, category), count in sorted(counts.items())]
    return [section("Why questions were missed"), table(["cause", "category", "misses"], rows)]
