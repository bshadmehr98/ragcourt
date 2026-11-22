"""``ragcourt audit``: check how chunkers cut your documents, by code, with no chat model (design §5).

Sizes come from the embedder's own token counts when it answers (measured), otherwise from characters / 4
(estimated, and said so). Exit code 3 when a check named by ``--fail-on`` fires.
"""

from __future__ import annotations

import argparse
import functools
import json
from pathlib import Path

from ragcourt import stages
from ragcourt.core.audit import CODES, MEANINGS, audit
from ragcourt.core.boundaries import mark_boundaries
from ragcourt.core.chunking import chunk_corpus
from ragcourt.core.sizes import summarize
from ragcourt.core.structure import structure_of
from ragcourt.errors import ConfigError
from ragcourt.io.audit_output import audit_data, audit_text
from ragcourt.io.documents import load_documents
from ragcourt.io.project import AddParser, Project, open_project, try_embedder
from ragcourt.stages.specs import check_params, parse_spec
from ragcourt.text_units import estimate_tokens
from ragcourt.types import Corpus, Embedder
from ragcourt.types.audit import AuditContext, AuditReport, ChunkerAudit

NAME = "audit"
HELP = "check how chunkers cut your documents (no chat model; sizes from the embedder, else estimated)"
NATIVE_CHUNKERS = ("fixed", "markdown", "recursive", "sentence")
# Input limits in force of common models, for when the embedder does not answer (design §5, D-041).
KNOWN_LIMITS = {
    "nomic-embed-text": 2048,
    "mxbai-embed-large": 512,
    "embeddinggemma": 2048,
    "bge-m3": 8192,
    "all-minilm": 512,
    "qwen3-embedding": 32768,
    "snowflake-arctic-embed": 512,
}
FAIL_EXIT = 3


def register(add_parser: AddParser, common: argparse.ArgumentParser) -> None:
    """Add ``audit`` and its options."""
    parser = add_parser(NAME, help=HELP, description=__doc__, parents=[common])
    parser.add_argument("folder", type=Path, help="the documents to audit")
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
    name = args.embedder or project.config.role("embedders").models[0]
    embedder, reason = try_embedder(project, name)
    specs = args.chunker or [*NATIVE_CHUNKERS, *project.user_stage_names("chunker")]
    report = build_report(project, corpus, specs, embedder, name, reason)
    _print(report, args, corpus)
    return FAIL_EXIT if fired_codes(report) & set(args.fail_on) else 0


def fired_codes(report: AuditReport) -> set[str]:
    """The checks that flagged at least one chunk."""
    fired: set[str] = set()
    for result in report.results:
        fired |= {finding.code for finding in result.findings}
    return fired


def build_report(
    project: Project, corpus: Corpus, specs: list[str], embedder: Embedder | None, name: str, reason: str
) -> AuditReport:
    """Chunk, size and check every chunker."""
    documents = {document.id: document for document in corpus.documents}
    structures = {document.id: structure_of(document.text) for document in corpus.documents}
    limit = embedder.max_tokens if embedder else KNOWN_LIMITS.get(name.split(":", maxsplit=1)[0])
    note = f"{name} did not answer ({reason}); sizes are estimated." if reason else ""
    if limit is None:
        note += " The input limit is unknown, so size.over_limit is skipped."
    results: list[ChunkerAudit] = []
    measured = embedder is not None
    for text in specs:
        spec = parse_spec(text)
        stage = stages.find("chunker", spec.name)
        check_params(stage.function, spec)
        chunked = chunk_corpus(
            corpus.documents, functools.partial(stage.function, **spec.kwargs()), str(spec)
        )
        sizes, counted = _sizes(embedder, [chunk.text for chunk in chunked.chunks])
        measured = measured and counted
        context = AuditContext(documents, structures, sizes, counted, limit, project.config.audit)
        findings = audit(chunked.chunks, context)
        results.append(
            ChunkerAudit(
                str(spec), chunked.chunks, chunked.dropped_empty, summarize(sizes, measured=counted), findings
            )
        )
    skipped = [(entry.path, entry.reason) for entry in corpus.skipped]
    shown_name = name if embedder else f"{name} (not reached)"
    return AuditReport(len(documents), skipped, shown_name, measured, limit, note.strip(), results)


def _sizes(embedder: Embedder | None, texts: list[str]) -> tuple[list[int], bool]:
    if embedder is not None and texts:
        counts = embedder.embed(texts).token_counts
        if counts is not None:
            return counts, True
    return [estimate_tokens(text) for text in texts], False


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
