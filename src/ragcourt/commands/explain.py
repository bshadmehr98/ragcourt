"""``ragcourt explain``: why each held-out question was missed, with evidence and a fix (design §9.3)."""

from __future__ import annotations

import argparse
import json

from ragcourt.core.blame import MEANINGS
from ragcourt.io import run_files
from ragcourt.io.explain_output import explain_text, show_text
from ragcourt.io.project import AddParser, open_project
from ragcourt.io.terminal import for_people

NAME = "explain"
HELP = "every missed question of a run: the stage, the mechanism, the evidence and the fix"


def register(add_parser: AddParser, common: argparse.ArgumentParser) -> None:
    """Add ``explain``."""
    parser = add_parser(NAME, help=HELP, description=for_people(__doc__), parents=[common])
    parser.add_argument("run_id", nargs="?", metavar="RUN", help="a run id (default: the latest)")
    parser.add_argument(
        "--show", metavar="QUESTION-ID", help="one miss with the chunk boundaries around its quote"
    )
    parser.add_argument("--json", action="store_true", help="print every miss as JSON")
    parser.set_defaults(run=run)


def run(args: argparse.Namespace) -> int:
    """Explain the run's misses."""
    project = open_project(args.options)
    folder = run_files.find_run(project.workdir, args.run_id)
    results = run_files.read_results(folder)
    if args.json:
        print(json.dumps(results["blames"], indent=1, ensure_ascii=False))
    elif args.show:
        print(show_text(results, args.show), end="")
    else:
        print(explain_text(results, MEANINGS, quiet=args.quiet), end="")
    return 0
