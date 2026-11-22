"""``ragcourt cache clear``: delete the embedding cache (design §10.2). Questions and runs are kept."""

from __future__ import annotations

import argparse
import shutil

from ragcourt.io.project import AddParser, open_project
from ragcourt.io.terminal import for_people

NAME = "cache"
HELP = "`cache clear` deletes the cached embeddings (questions and runs are kept)"


def register(add_parser: AddParser, common: argparse.ArgumentParser) -> None:
    """Add ``cache``."""
    parser = add_parser(NAME, help=HELP, description=for_people(__doc__), parents=[common])
    parser.add_argument("action", choices=["clear"], help="clear the embedding cache")
    parser.set_defaults(run=run)


def run(args: argparse.Namespace) -> int:
    """Clear the cache."""
    project = open_project(args.options)
    folder = project.workdir / "cache" / "embeddings"
    if folder.exists():
        shutil.rmtree(folder)
    print(f"Cleared {folder}.")
    return 0
