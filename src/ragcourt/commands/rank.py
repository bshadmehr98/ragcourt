"""``ragcourt rank``: rank chunkers, embedders, retrievers and rerankers on your documents (design §8to§10).

Prints the plan (every role, model, where it came from, what it is shown, the time estimate) before any
model call; writes or reuses the questions; runs the greedy search with leaderboards on held-out questions;
blames every miss; writes ``.ragcourt/runs/<run>/results.json`` (and ``report.html`` with ``--html``).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ragcourt.core.blame import MEANINGS
from ragcourt.flows.questions import QuestionOptions
from ragcourt.flows.rank import run_rank
from ragcourt.flows.run_plan import QUICK_PER_CATEGORY, RankOptions
from ragcourt.io import run_files
from ragcourt.io.documents import load_documents
from ragcourt.io.html_report import write_report
from ragcourt.io.project import AddParser, open_project
from ragcourt.io.rank_output import summary_text
from ragcourt.io.terminal import for_people

NAME = "rank"
HELP = "rank pipelines on your documents with intervals, and blame every miss (shows its plan first)"


def names(text: str | None, separator: str = ",") -> tuple[str, ...] | None:
    """A list from a flag. Chunker specs hold commas (``recursive:size=256,overlap=32``), so they are
    separated by ``;``."""
    if not text:
        return None
    return tuple(part.strip() for part in text.split(separator) if part.strip())


def register(add_parser: AddParser, common: argparse.ArgumentParser) -> None:
    """Add ``rank`` and its options."""
    parser = add_parser(NAME, help=HELP, description=for_people(__doc__), parents=[common])
    parser.add_argument("folder", type=Path, help="the documents")
    parser.add_argument(
        "--resume", action="store_true", help="continue the last unfinished run with the same plan"
    )
    size = parser.add_mutually_exclusive_group()
    size.add_argument("--questions", type=int, metavar="N", help="questions per category (default 90)")
    size.add_argument(
        "--quick",
        action="store_true",
        help=f"a quick look: {QUICK_PER_CATEGORY} questions per category; shows the misses, names no winner",
    )
    parser.add_argument(
        "--questions-file", type=Path, metavar="FILE", help="your own questions with quotes (JSONL)"
    )
    parser.add_argument("--writer", metavar="MODEL", help="the question writer for this run")
    parser.add_argument("--judge", metavar="MODEL", help="the judge for this run")
    parser.add_argument("--metric", help="the metric to rank by (default recall_at_budget)")
    parser.add_argument("--k", type=int, help="how many chunks count (default 5)")
    parser.add_argument("--embedders", metavar="LIST", help="embedders to compare, comma-separated")
    parser.add_argument("--chunkers", metavar="LIST", help="chunkers to compare; separate specs with ';'")
    parser.add_argument("--retrievers", metavar="LIST", help="retrievers to compare, comma-separated")
    parser.add_argument("--rerankers", metavar="LIST", help="rerankers to compare, comma-separated")
    parser.add_argument(
        "--budget-minutes", type=float, metavar="M", help="stop before a step that would pass M minutes"
    )
    parser.add_argument("--budget-usd", type=float, metavar="X", help="refuse a run that would cost over $X")
    parser.add_argument("--yes", action="store_true", help="start without asking")
    parser.add_argument("--html", action="store_true", help="also write a self-contained report.html")
    parser.set_defaults(run=run)


def run(args: argparse.Namespace) -> int:
    """Plan, run and report."""
    project = open_project(args.options)
    corpus = load_documents(args.folder)
    per_category = QUICK_PER_CATEGORY if args.quick else args.questions
    questions = QuestionOptions(per_category, args.judge, args.writer, args.questions_file)
    options = RankOptions(
        questions,
        args.metric,
        args.k,
        names(args.embedders),
        names(args.chunkers, ";"),
        names(args.retrievers),
        names(args.rerankers),
        args.budget_minutes,
        args.budget_usd,
        yes=args.yes,
        resume=args.resume,
        quick=args.quick,
    )
    folder = run_rank(project, corpus, options, print)
    if folder is None:
        return 0
    results = run_files.read_results(folder)
    print(summary_text(results, quiet=args.quiet), end="")
    print(f"Results: {folder / run_files.RESULTS}")
    if args.html:
        print(f"Report: {write_report(folder, results, MEANINGS)}")
    return 0
