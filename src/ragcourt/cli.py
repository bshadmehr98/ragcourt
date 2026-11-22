"""The command line: ``ragcourt <command>`` (design §13.1). Each command is one file in ``commands/``.

Exit codes: 0 done, 1 error, 2 usage, 3 a ``--fail-on`` check fired, 4 stopped by the budget.
"""

from __future__ import annotations

import argparse
import sys
from importlib.metadata import version
from pathlib import Path

from ragcourt.commands import audit
from ragcourt.errors import BudgetExceeded, RagCourtError
from ragcourt.io.project import ProjectOptions

COMMANDS = [audit]
BUDGET_EXIT = 4


def common_options() -> argparse.ArgumentParser:
    """The options every command takes."""
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--workdir", type=Path, help="where ragcourt keeps its files (default .ragcourt/)")
    common.add_argument("--config", type=Path, help="the configuration file (default ragcourt.toml)")
    common.add_argument(
        "--stages", type=Path, help="the folder of your own stages (default ragcourt_stages/)"
    )
    common.add_argument("--seed", type=int, help="the seed of every random choice")
    common.add_argument("--json", action="store_true", help="write data instead of text")
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
    """Run one command; errors print one message, never a traceback."""
    args = build_parser().parse_args(argv)
    args.options = ProjectOptions(Path.cwd(), args.config, args.stages, args.workdir, args.seed)
    try:
        return int(args.run(args))
    except BudgetExceeded as error:
        print(f"ragcourt: {error}", file=sys.stderr)
        return BUDGET_EXIT
    except RagCourtError as error:
        print(f"ragcourt: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("ragcourt: interrupted; `rank --resume` continues where it stopped.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
