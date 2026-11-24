"""The audit of a corpus by several chunkers, shared by ``audit`` and ``demo`` (design §5).

Sizes come from the embedder's own token counts when there is one (measured), otherwise from characters / 4
(estimated, and said so).
"""

from __future__ import annotations

import functools

from ragcourt import stages
from ragcourt.core.audit import audit
from ragcourt.core.chunking import chunk_corpus
from ragcourt.core.sizes import summarize
from ragcourt.core.structure import structure_of
from ragcourt.io.documents import PDF_SUFFIX
from ragcourt.io.pdf_text import extractor
from ragcourt.io.terminal import plural
from ragcourt.stages.specs import check_params, parse_spec
from ragcourt.text_units import estimate_tokens
from ragcourt.types import Corpus, Embedder
from ragcourt.types.audit import AuditContext, AuditReport, AuditSettings, ChunkerAudit

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


def build_report(
    settings: AuditSettings, corpus: Corpus, specs: list[str], counted_by: tuple[Embedder | None, str, str]
) -> AuditReport:
    """Chunk, size and check every chunker; ``counted_by`` is the embedder (or None), its name, and why
    it did not answer."""
    embedder, name, reason = counted_by
    documents = {document.id: document for document in corpus.documents}
    structures = {document.id: structure_of(document.text) for document in corpus.documents}
    limit = embedder.max_tokens if embedder else KNOWN_LIMITS.get(name.split(":", maxsplit=1)[0])
    note = f"{name} did not answer ({reason}); sizes are estimated." if reason else ""
    if limit is None:
        note += " The input limit is unknown, so size.over_limit is skipped."
    pdfs = sum(1 for name in documents if name.lower().endswith(PDF_SUFFIX))
    if pdfs:
        note += f" {plural(pdfs, 'document')} from PDF, as text extracted by {extractor()}."
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
        context = AuditContext(documents, structures, sizes, counted, limit, settings)
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
