"""``ragcourt audit``: check how chunkers cut your documents, by code, with no chat model (design §5).

Sizes come from the embedder's own token counts when it answers (measured), otherwise from characters / 4
(estimated, and said so). Exit code 3 when a check named by ``--fail-on`` fires.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ragcourt.core.audit import CODES, MEANINGS
from ragcourt.core.boundaries import mark_boundaries
from ragcourt.errors import ConfigError
from ragcourt.flows.audit import build_report
from ragcourt.io.audit_output import audit_data, audit_text
from ragcourt.io.documents import load_documents
from ragcourt.io.project import AddParser, open_project, try_embedder
from ragcourt.io.terminal import for_people
from ragcourt.types import Corpus
from ragcourt.types.audit import AuditReport, CountedBy

NAME = "audit"
HELP = "check how chunkers cut your documents (no chat model; sizes from the embedder, else estimated)"
NATIVE_CHUNKERS = ("fixed", "markdown", "recursive", "sentence")
FAIL_EXIT = 3


def register(add_parser: AddParser, common: argparse.ArgumentParser) -> None:
    """Add ``audit`` and its options."""
    parser = add_parser(NAME, help=HELP, description=for_people(__doc__), parents=[common])
    parser.add_argument("folder", type=Path, help="the documents to audit")
    parser.add_argument("--json", action="store_true", help="print the audit as JSON")
    parser.add_argument(
        "--chunker",
        action="append",
        default=[],
        metavar="SPEC",
        help="a chunker, e.g. recursive:size=256 (repeatable)",
    )
    parser.add_argument(
        "--embedder", help="whose tokens to count in (default: the first embedder in [models])"
    )
    parser.add_argument("--show", metavar="DOC", help="print this document with the chunk boundaries marked")
    parser.add_argument(
        "--fail-on", nargs="+", default=[], metavar="CODE", help="exit 3 when one of these checks fires"
    )
    parser.set_defaults(run=run)


def run(args: argparse.Namespace) -> int:
    """Audit every chunker asked for (default: the native ones and your own) on the folder."""
    unknown = [code for code in args.fail_on if code not in CODES]
    if unknown:
        raise ConfigError(f"Unknown check {', '.join(unknown)}; the checks are {', '.join(CODES)}.")
    project = open_project(args.options)
    corpus = load_documents(args.folder)
    if not corpus.documents:
        reasons = "".join(f"\n  skipped {entry.path}: {entry.reason}" for entry in corpus.skipped)
        raise ConfigError(
            f"No documents to audit in {args.folder}: give .md, .txt, .rst, .html or .pdf files.{reasons}"
        )
    name = args.embedder or project.config.role("embedders").models[0]
    embedder, reason = try_embedder(project, name)
    specs = args.chunker or [*NATIVE_CHUNKERS, *project.user_stage_names("chunker")]
    report = build_report(project.config.audit, corpus, specs, CountedBy(embedder, name, reason))
    _print(report, args, corpus)
    return FAIL_EXIT if fired_codes(report) & set(args.fail_on) else 0


def fired_codes(report: AuditReport) -> set[str]:
    """The checks that flagged at least one chunk."""
    fired: set[str] = set()
    for result in report.results:
        fired |= {finding.code for finding in result.findings}
    return fired


def _print(report: AuditReport, args: argparse.Namespace, corpus: Corpus) -> None:
    if args.json:
        print(json.dumps(audit_data(report), indent=2))
    else:
        print(audit_text(report, CODES, MEANINGS, quiet=args.quiet), end="")
    if args.show:
        _show(report, args.show, corpus)


def _show(report: AuditReport, document_id: str, corpus: Corpus) -> None:
    texts = {document.id: document.text for document in corpus.documents}
    if document_id not in texts:
        raise ConfigError(
            f"No document {document_id!r} in the folder; ids are paths like {next(iter(texts), 'a.md')!r}."
        )
    for result in report.results:
        chunks = [chunk for chunk in result.chunks if chunk.document == document_id]
        flags: dict[int, list[str]] = {}
        for finding in result.findings:
            flags.setdefault(finding.chunk.index, []).append(finding.code)
        print(f"\n--- {document_id} cut by {result.chunker} ---")
        print(mark_boundaries(texts[document_id], chunks, flags))
