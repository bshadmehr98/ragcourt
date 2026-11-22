"""``ragcourt doctor``: a model looks at samples of your documents, recommends chunkers and may write one.

Everything it suggests is measured against the built-in chunkers on the same held-out questions. Code the
model writes is printed in full with its SHA-256 and runs only after you answer yes, or with ``--approve``
naming exactly that hash; it runs in a separate process with a timeout, which is not a sandbox (§12).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ragcourt.flows.doctor import DoctorOptions, run_doctor
from ragcourt.flows.questions import QuestionOptions
from ragcourt.io.documents import load_documents
from ragcourt.io.project import AddParser, open_project
from ragcourt.io.terminal import for_people

NAME = "doctor"
HELP = "a model recommends (and may write) a chunker; everything is measured; code runs only if you approve"


def register(add_parser: AddParser, common: argparse.ArgumentParser) -> None:
    """Add ``doctor``."""
    parser = add_parser(NAME, help=HELP, description=for_people(__doc__), parents=[common])
    parser.add_argument("folder", type=Path, help="the documents")
    parser.add_argument(
        "--approve", metavar="SHA256", help="run the generated chunker if its hash is exactly this"
    )
    parser.add_argument("--no-code", action="store_true", help="do not ask the model to write a chunker")
    parser.add_argument(
        "--timeout", type=float, default=10.0, help="seconds per document for the generated chunker"
    )
    parser.add_argument("--questions", type=int, metavar="N", help="questions per category (default 90)")
    parser.add_argument("--embedder", help="the embedder to measure with (default: the first in [models])")
    parser.set_defaults(run=run)


def run(args: argparse.Namespace) -> int:
    """Run doctor."""
    project = open_project(args.options)
    corpus = load_documents(args.folder)
    options = DoctorOptions(
        QuestionOptions(args.questions), args.approve, not args.no_code, args.timeout, args.embedder
    )
    return run_doctor(project, corpus, options, print)
