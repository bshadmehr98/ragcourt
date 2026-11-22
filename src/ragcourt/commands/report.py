"""``ragcourt report``: write the self-contained HTML report of a run (design §13.4)."""

from __future__ import annotations

import argparse

from ragcourt.core.blame import MEANINGS
from ragcourt.io import run_files
from ragcourt.io.html_report import write_report
from ragcourt.io.project import AddParser, open_project

NAME = "report"
HELP = "write report.html for a run: one file, no network requests"


def register(add_parser: AddParser, common: argparse.ArgumentParser) -> None:
    """Add ``report``."""
    parser = add_parser(NAME, help=HELP, description=__doc__, parents=[common])
    parser.add_argument("run_id", nargs="?", metavar="RUN", help="a run id (default: the latest)")
    parser.set_defaults(run=run)


def run(args: argparse.Namespace) -> int:
    """Write the report and say where."""
    project = open_project(args.options)
    folder = project.workdir / "runs" / args.run_id if args.run_id else run_files.latest_run(project.workdir)
    print(write_report(folder, run_files.read_results(folder), MEANINGS))
    return 0
