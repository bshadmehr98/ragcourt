"""The command line: ``ragcourt <command>`` (design §13.1). Each command is one file in ``commands/``.

Exit codes: 0 done, 1 error, 2 usage, 3 a ``--fail-on`` check fired, 4 stopped by the budget.
"""

from __future__ import annotations

import argparse
import io
import sys
from importlib.metadata import version
from pathlib import Path
from typing import TextIO

from ragcourt.commands import audit, cache, doctor, explain, models, prompts, questions, rank, report, setup
from ragcourt.errors import BudgetExceeded, RagCourtError
from ragcourt.io.lock import workdir_lock
from ragcourt.io.project import WORKDIR, ProjectOptions
from ragcourt.io.terminal import printable

COMMANDS = [setup, models, prompts, audit, questions, rank, explain, report, doctor, cache]
BUDGET_EXIT = 4
WRITERS = {"audit", "questions", "rank", "doctor", "cache"}  # commands that write the working folder


def common_options() -> argparse.ArgumentParser:
    """The options every command takes."""
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--workdir", type=Path, help="where ragcourt keeps its files (default .ragcourt/)")
    common.add_argument("--config", type=Path, help="the configuration file (default ragcourt.toml)")
    common.add_argument(
        "--stages", type=Path, help="the folder of your own stages (default ragcourt_stages/)"
    )
    common.add_argument("--seed", type=int, help="the seed of every random choice")
    common.add_argument("-q", "--quiet", action="store_true", help="leave out legends and explanations")
    return common


def build_parser() -> argparse.ArgumentParser:
    """The parser with every command."""
    parser = argparse.ArgumentParser(
        prog="ragcourt",
        description="Rank chunkers, embedders, retrievers and rerankers on your own documents, "
        "and say which stage caused each miss.",
    )
    parser.add_argument("--version", action="version", version=f"ragcourt {version('ragcourt')}")
    subparsers = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")
    common = common_options()
    for command in COMMANDS:
        command.register(subparsers.add_parser, common)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run one command; errors print one message, never a traceback. Text from documents and models can
    hold terminal escapes, so everything printed is made printable (D-057)."""
    _readable_output()
    streams = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = SafeStream(sys.stdout), SafeStream(sys.stderr)
    try:
        return _run(argv)
    finally:
        sys.stdout, sys.stderr = streams


def _run(argv: list[str] | None) -> int:
    args = build_parser().parse_args(argv)
    args.options = ProjectOptions(Path.cwd(), args.config, args.stages, args.workdir, args.seed)
    try:
        return _command(args)
    except BudgetExceeded as error:
        print(f"ragcourt: {error}", file=sys.stderr)
        return BUDGET_EXIT
    except RagCourtError as error:
        print(f"ragcourt: {error}", file=sys.stderr)
        return 1
    except OSError as error:  # a folder that cannot be written, a full disk
        print(f"ragcourt: {error.strerror or error}: {error.filename or ''}".rstrip(": "), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("ragcourt: interrupted; `rank --resume` continues where it stopped.", file=sys.stderr)
        return 130


def _command(args: argparse.Namespace) -> int:
    if args.command not in WRITERS:
        return int(args.run(args))
    with workdir_lock(args.workdir or Path.cwd() / WORKDIR):
        return int(args.run(args))


class SafeStream:
    """A terminal stream that writes escapes in place of control and bidirectional characters."""

    def __init__(self, stream: TextIO) -> None:
        self.stream = stream

    def write(self, text: str) -> int:
        return self.stream.write(printable(text))

    def flush(self) -> None:
        self.stream.flush()

    def isatty(self) -> bool:
        return self.stream.isatty()


def _readable_output() -> None:
    """Progress reaches a log file line by line, and a console that cannot show a character (⟦, «) gets a
    replacement instead of a crash."""
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(line_buffering=True, errors="replace")


if __name__ == "__main__":
    sys.exit(main())
