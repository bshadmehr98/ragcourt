"""``ragcourt questions``: write the question set for a folder, or show it with every verdict (design §6).

``ragcourt questions FOLDER`` writes (or reuses, or resumes) the questions; ``ragcourt questions show``
lists them with their quotes and the reason of every check; ``--dropped`` lists what was dropped and why.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ragcourt.flows.questions import QuestionOptions, ensure_questions
from ragcourt.io import question_file
from ragcourt.io.documents import load_documents
from ragcourt.io.project import AddParser, open_project
from ragcourt.io.question_output import show_text, summary_text

NAME = "questions"
HELP = "write the question set (the writer and judge models), or `questions show` to read it"


def register(add_parser: AddParser, common: argparse.ArgumentParser) -> None:
    """Add ``questions`` and its options."""
    parser = add_parser(NAME, help=HELP, description=__doc__, parents=[common])
    parser.add_argument("folder", help="the documents, or `show` to list the question set")
    parser.add_argument("--questions", type=int, metavar="N", help="questions per category (default 90)")
    parser.add_argument(
        "--questions-file", type=Path, metavar="FILE", help="your own questions with quotes (JSONL)"
    )
    parser.add_argument("--judge", metavar="MODEL", help="the judge for this run")
    parser.add_argument("--writer", metavar="MODEL", help="the question writer for this run")
    parser.add_argument("--dropped", action="store_true", help="with show: list dropped questions and why")
    parser.add_argument(
        "--reason", metavar="TEXT", help="with show --dropped: only drops whose reason has TEXT"
    )
    parser.set_defaults(run=run)


def run(args: argparse.Namespace) -> int:
    """Write or show the question set."""
    project = open_project(args.options)
    if args.folder == "show":
        found = question_file.read_questions(project.workdir)
        questions, dropped = (found[1], found[2]) if found else ([], [])
        print(show_text(questions, dropped, show_dropped=args.dropped, reason=args.reason), end="")
        return 0
    corpus = load_documents(Path(args.folder))
    options = QuestionOptions(args.questions, args.judge, args.writer, args.questions_file)
    questions = ensure_questions(project, corpus, options, print)
    found = question_file.read_questions(project.workdir)
    dropped = found[2] if found else []
    print(summary_text(questions, dropped, project.config.questions.min_held_out, quiet=args.quiet), end="")
    return 0
