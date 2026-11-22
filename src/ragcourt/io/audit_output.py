"""Writing the audit for people and for programs (design §5.2)."""

from __future__ import annotations

from typing import Any

from ragcourt.io.terminal import legend, plural, section, table
from ragcourt.types.audit import AuditReport, ChunkerAudit, Finding

EXAMPLES_PER_CHECK = 2


def audit_text(report: AuditReport, codes: list[str], meanings: dict[str, str], *, quiet: bool) -> str:
    """The audit as plain text: sizes, findings per check and chunker, examples, and the legend."""
    lines = [_header(report)]
    if report.note:
        lines.append(f"Note: {report.note}")
    size_rows = [_size_row(result) for result in report.results]
    lines += [
        section("Chunk sizes (tokens)"),
        table(["chunker", "chunks", "median", "p95", "max", "sizes"], size_rows),
    ]
    names = [result.chunker for result in report.results]
    rows: list[list[object]] = []
    for code in codes:
        rows.append([code, *[_count(result, code) for result in report.results]])
    lines += [section("Findings: chunks flagged (share)"), table(["check", *names], rows)]
    lines += _examples(report.results)
    if not quiet:
        lines += ["", legend({code: f"flags a chunk that {meanings[code]}" for code in codes})]
    return "\n".join(lines) + "\n"


def _header(report: AuditReport) -> str:
    limit = "unknown" if report.limit is None else f"{report.limit} tokens"
    sizes = "measured" if report.sizes_measured else "estimated (characters / 4)"
    skipped = f", {len(report.skipped)} skipped" if report.skipped else ""
    chunkers = plural(len(report.results), "chunker")
    lines = [
        f"Audit of {plural(report.documents, 'document')}{skipped} with {chunkers}.",
        f"Sizes: {sizes}, by {report.embedder}; input limit: {limit}.",
    ]
    lines += [f"  skipped {path}: {reason}" for path, reason in report.skipped]
    return "\n".join(lines)


def _size_row(result: ChunkerAudit) -> list[object]:
    size = result.size
    return [result.chunker, len(result.chunks), size.median, size.p95, size.largest, size.label]


def _count(result: ChunkerAudit, code: str) -> str:
    count = sum(1 for finding in result.findings if finding.code == code)
    share = count / len(result.chunks) if result.chunks else 0.0
    return f"{count} ({share:.0%})"


def _examples(results: list[ChunkerAudit]) -> list[str]:
    lines: list[str] = []
    for result in results:
        shown: dict[str, int] = {}
        picked: list[Finding] = []
        for finding in result.findings:
            if shown.get(finding.code, 0) < EXAMPLES_PER_CHECK:
                shown[finding.code] = shown.get(finding.code, 0) + 1
                picked.append(finding)
        if not picked:
            continue
        lines.append(section(f"Examples: {result.chunker}"))
        for finding in picked:
            chunk = finding.chunk
            where = f"{chunk.document} [{chunk.start}:{chunk.end}] chunk {chunk.index}"
            lines.append(f"- {finding.code}: {where}: {finding.detail}")
            lines.append(f"    starts {chunk.text[:60]!r}")
            lines.append(f"    ends   {chunk.text[-60:]!r}")
    return lines


def audit_data(report: AuditReport) -> dict[str, Any]:
    """The audit as data for ``--json``."""
    return {
        "documents": report.documents,
        "skipped": [{"path": path, "reason": reason} for path, reason in report.skipped],
        "embedder": report.embedder,
        "sizes": "measured" if report.sizes_measured else "estimated",
        "limit": report.limit,
        "note": report.note,
        "chunkers": [_chunker_data(result) for result in report.results],
    }


def _chunker_data(result: ChunkerAudit) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for finding in result.findings:
        counts[finding.code] = counts.get(finding.code, 0) + 1
    findings = [
        {
            "code": f.code,
            "document": f.chunk.document,
            "chunk": f.chunk.index,
            "start": f.chunk.start,
            "end": f.chunk.end,
            "detail": f.detail,
        }
        for f in result.findings
    ]
    size = {
        "median": result.size.median,
        "p95": result.size.p95,
        "max": result.size.largest,
        "label": result.size.label,
    }
    return {
        "chunker": result.chunker,
        "chunks": len(result.chunks),
        "dropped_empty": result.dropped_empty,
        "size": size,
        "counts": counts,
        "findings": findings,
    }
