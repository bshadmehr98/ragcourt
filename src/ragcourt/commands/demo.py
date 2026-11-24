"""``ragcourt demo``: what ragcourt finds, in under a minute, with no model and no network (change 0003).

The audit is computed now on the documents bundled with ragcourt. The ranking, its misses and the report
are a real run on those documents, recorded once with local models and shipped with the package; every
recorded number is printed under a line that says when, with which models and on which machine. Nothing is
contacted, and one file is written: ``.ragcourt/demo/report.html``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ragcourt import stages
from ragcourt.core.audit import CODES
from ragcourt.core.audit import MEANINGS as CHECKS
from ragcourt.core.blame import MEANINGS
from ragcourt.flows.audit import build_report
from ragcourt.io import run_files
from ragcourt.io.audit_output import audit_text
from ragcourt.io.documents import load_documents
from ragcourt.io.explain_output import misses_text
from ragcourt.io.html_report import write_report
from ragcourt.io.project import WORKDIR, AddParser
from ragcourt.io.rank_output import board_text, chosen_note, summary_text
from ragcourt.io.terminal import for_people, plural, section
from ragcourt.types.audit import AuditSettings, CountedBy

NAME = "demo"
HELP = "see what ragcourt finds in under a minute: no model, no network (a recorded real run)"
PACKAGE = Path(__file__).resolve().parent.parent
RECORDING = PACKAGE / "demo"  # results.json of a real run on the bundled corpus, and recording.json
CORPUS = (
    PACKAGE / "testing" / "corpus"
)  # what ragcourt.testing.corpus_path() gives; commands may not import testing
CHUNKERS = ["recursive", "fixed:size=128,overlap=0"]
MISSES_SHOWN = 3


def register(add_parser: AddParser, common: argparse.ArgumentParser) -> None:
    """Add ``demo``."""
    parser = add_parser(NAME, help=HELP, description=for_people(__doc__), parents=[common])
    parser.set_defaults(run=run)


def recorded_line(results: dict[str, Any], recording: dict[str, str]) -> str:
    """When, with which models and on which machine the recorded run was made."""
    models: list[str] = []
    for role in results["plan"]["roles"]:
        models += [model for model in role["models"] if model not in models]
    return (
        f"Recorded on {recording['date']} with {', '.join(models)} on {recording['machine']}: "
        f"{plural(results['questions']['total'], 'question')}, {results['time_minutes']:.0f} minutes; "
        f"{recording['note']}.\nThese are numbers of the bundled documents, not of yours."
    )


def run(args: argparse.Namespace) -> int:
    """The live audit, then the recorded run printed as ``rank`` and ``explain`` print it."""
    stages.load_builtins()
    corpus = load_documents(CORPUS)
    counted_by = CountedBy(None, "nomic-embed-text", "not asked: the demo contacts no model")
    report = build_report(AuditSettings(), corpus, CHUNKERS, counted_by)
    print(section(f"1. Audit, computed now on the {len(corpus.documents)} bundled documents"))
    print(audit_text(report, CODES, CHECKS, quiet=True), end="")
    results = run_files.read_results(RECORDING)
    recording = json.loads((RECORDING / "recording.json").read_text(encoding="utf-8"))
    print(section("2. A ranking of the same documents, recorded with real local models"))
    print(recorded_line(results, recording))
    for board, step in zip(results["boards"], results["steps"], strict=True):
        print(board_text(board, chosen_note(str(step["chosen"]), len(step["tied_on_dev"]))))
    print(summary_text(results, quiet=args.quiet), end="")
    blames = results["blames"]
    print(section(f"3. {min(MISSES_SHOWN, len(blames))} of its {len(blames)} misses, explained"))
    print("\n".join(misses_text(blames[:MISSES_SHOWN])))
    folder = (args.workdir or Path.cwd() / WORKDIR) / "demo"
    folder.mkdir(parents=True, exist_ok=True)
    print(section("4. The same as one page"))
    print(write_report(folder, results, MEANINGS))
    print("\nNow your documents: `ragcourt setup`, then `ragcourt rank DOCS --quick`.")
    return 0
