"""Writing a run for people: the plan, the leaderboards, ceilings, blame and the legend (design §13.2).

Everything is rendered from plain data (the contents of ``results.json``), so ``rank``, ``explain`` and
``report`` say the same thing.
"""

from __future__ import annotations

from typing import Any

from ragcourt.io.plan_output import quick_note
from ragcourt.io.terminal import legend, plural, section, table

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
        lines.append(f"{name}: too few to rank ({plural(count, 'held-out question')}).")
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
    """Said when the pipeline chosen on dev is separably worse on held-out than the top (D-057)."""
    rows = board["rows"]
    label = chosen.split(" (tied on dev", maxsplit=1)[0]
    behind = [row for row in rows[1:] if row["label"] == label and not row["tied_with_top"]]
    if not rows or not behind:
        return []
    return [
        f"Note: on held-out questions {rows[0]['label']} is separably better than this choice; the dev "
        "questions could not tell them apart. Prefer it, or write more questions (--questions N)."
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
    if board["stage"] == "pipeline" and len(board["rows"]) == 1:
        return (
            "Your pipeline alone: without --no-search it is compared with the best pipeline ragcourt finds."
        )
    if board["winner"]:
        return f"Winner: {board['winner']}."
    tied = ", ".join(row["label"] for row in board["rows"] if row["tied_with_top"])
    return f"No significant difference between {board['rows'][0]['label']} and {tied}: no winner."


def summary_text(results: dict[str, Any], *, quiet: bool) -> str:
    """The end of a run: the chosen pipeline, its ceilings, the causes of its misses, and the legend."""
    rows = [_ceiling_row(name, value) for name, value in results["ceilings"].items()]
    title = "Your pipeline" if results.get("pipeline") else "Chosen pipeline"
    lines = [section(title), results["chosen"], section("Ceilings (held-out)")]
    lines += [table(["group", "questions", "chunker", "retrieval", "hit@k"], rows), *causes_text(results)]
    share = results.get("confirmed_share")
    if share is not None:
        lines.append(f"\n{share:.0%} of blames are confirmed by a measured alternative; the rest by probes.")
    lines.append("Every miss, with its evidence and fix: `ragcourt explain`.")
    if results["plan"].get("quick"):
        lines += ["", quick_note(results["plan"]["quick"])]
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


def chosen_note(label: str, tied: int) -> str:
    """The chosen entry, and the rule that chose it among ties (a held-out disagreement is said under
    the board)."""
    if not tied:
        return label
    rule = "kept the cheaper, then the higher on dev, then the smaller"
    return f"{label} (tied on dev with {tied} more; {rule})"


def placed_note(pipeline: dict[str, Any]) -> str:
    """Under the board of the user's own pipeline: how many of its texts could be placed and scored."""
    lost = pipeline["not_found"] + pipeline["several"]
    lines = [
        f"{pipeline['texts'] - lost} of {pipeline['texts']} chunk texts of {pipeline['name']} were found "
        "in your documents."
    ]
    if pipeline["not_found"]:
        lines.append(
            f"{pipeline['not_found']} are not text of your documents (rewritten, or a title or summary "
            "added): they hold no quote, and their words count against precision and the token budget."
        )
    if pipeline["several"]:
        lines.append(
            f"{pipeline['several']} are found in more than one place: their place is unknown, so they are "
            "counted the same way."
        )
    if not pipeline["chunks_known"]:
        lines.append(
            "Its chunks are not listed, so nDCG is measured against a chunk that holds the whole quote."
        )
    return "\n".join(lines)


def failure_note(label: str, count: int) -> str:
    """Said under a board when a reranker's calls were refused for some questions (D-057)."""
    return (
        f"Note: the reranker of {label} failed on {plural(count, 'question')} (the server "
        "refused the call twice); their retrieval order was kept, so its score is a little low."
    )


def weak_spot_note(category: str, chosen_mean: float, better: str, better_mean: float) -> str:
    """Said under a board when the choice is separably behind another entry on one kind of question."""
    return (
        f"Note: on {category} questions this choice scores {chosen_mean:.2f}, separably below {better} "
        f"({better_mean:.2f}). If those questions matter to you, prefer it."
    )
