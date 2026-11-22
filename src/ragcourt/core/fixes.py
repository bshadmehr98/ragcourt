"""Fixes and evidence levels: what would have found a missed question, measured or not (design §9.3).

``confirmed``: a configuration measured in this run that differs from the chosen one only in the blamed
stage hits the question, and the fix names it. ``indicated``: the probes point to the mechanism but no such
configuration was measured; the fix says "not measured" and gives the command that would measure it.
"""

from __future__ import annotations

from ragcourt.types.results import Evaluation, PipelineSpec

FIELDS = {
    "chunker": ("chunker",),
    "embedder": ("embedder",),
    "retriever": ("retriever",),
    "ranking": ("reranker",),
}
FLAGS = {
    "chunker": "--chunkers",
    "embedder": "--embedders",
    "retriever": "--retrievers",
    "reranker": "--rerankers",
}
FIXES = {
    "chunker.too_small": "a chunker with larger chunks",
    "chunker.split": "a chunker that keeps this passage whole",
    "chunker.dropped": "a chunker that keeps all of the text",
    "chunker.over_limit": "a smaller chunk size, or an embedder with a longer input limit",
    "chunker.diluted": "a smaller or section-aware chunker",
    "embedder.exact_words": "hybrid retrieval, or an embedder that finds exact terms",
    "embedder.distracted": "a reranker, or an embedder that ranks the answer above its look-alike",
    "embedder.meaning": "another embedder",
    "retriever.keyword_only": "dense or hybrid retrieval",
    "retriever.fusion": "other fusion weights, or the half of the hybrid that finds it",
    "retriever.crowded": "removing the near-duplicates (the audit lists them)",
    "ranking.reranker_demoted": "no reranker, or another one",
    "ranking.distracted": "a reranker",
    "ranking.duplicates": "removing the near-duplicates (the audit lists them)",
    "ranking.not_rescued": "a reranker that lifts it, or a larger k",
}


def fix_for(
    mechanism: str, question: str, chosen: PipelineSpec, measured: list[Evaluation]
) -> tuple[str, str]:
    """The evidence level and the fix of one blame."""
    stage = mechanism.split(".", maxsplit=1)[0]
    fields = ("chunker", "embedder") if mechanism == "chunker.over_limit" else FIELDS[stage]
    tried: list[str] = []
    for evaluation in measured:
        changed = chosen.differs_only_in(evaluation.spec)
        if len(changed) != 1 or changed[0] not in fields:
            continue
        value = f"{changed[0]} {getattr(evaluation.spec, changed[0])}"
        result = evaluation.results.get(question)
        if result and result.metrics["hit_at_k"] == 1.0:
            return "confirmed", f"{FIXES[mechanism]}: {value} finds it (measured in this run)"
        if value not in tried:
            tried.append(value)
    if mechanism == "embedder.meaning" and _no_embedder_finds(question, measured):
        return "indicated", "no tested embedder connects this question to its answer"
    if tried:
        return "indicated", f"{FIXES[mechanism]}; measured here and not finding it either: {', '.join(tried)}"
    flag = FLAGS[fields[0]]
    return "indicated", f"{FIXES[mechanism]} (not measured: `ragcourt rank DOCS {flag} …` would measure it)"


def _no_embedder_finds(question: str, measured: list[Evaluation]) -> bool:
    results = [
        evaluation.results.get(question) for evaluation in measured if evaluation.spec.retriever == "dense"
    ]
    return all(result is None or result.metrics["hit_at_k"] == 0.0 for result in results)
