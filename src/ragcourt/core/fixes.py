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
    near: list[str] = []
    for evaluation in measured:
        changed = _changed(chosen, evaluation.spec, fields)
        if not changed or changed[0] not in fields:
            continue
        value = " and ".join(f"{name} {getattr(evaluation.spec, name)}" for name in changed)
        hit = _hits(evaluation, question)
        if hit and len(changed) == 1:
            return (
                "confirmed",
                f"{FIXES[mechanism]}: with {value} it reaches the top k (measured in this run)",
            )
        # One other stage changed too: still evidence, for any stage but the reranker (whose "with
        # reranker none" would read as the opposite of the fix).
        allowed = 1 if stage == "ranking" else 2
        if len(changed) > allowed:
            continue
        if hit and value not in near:
            near.append(value)
        elif not hit and value not in tried:
            tried.append(value)
    return "indicated", _indicated(mechanism, question, measured, (tried, near, FLAGS[fields[0]]))


def _indicated(
    mechanism: str, question: str, measured: list[Evaluation], found: tuple[list[str], list[str], str]
) -> str:
    tried, near, flag = found
    if mechanism == "embedder.meaning" and _no_embedder_finds(question, measured):
        return "no tested embedder connects this question to its answer"
    if near:  # measured, but with another stage changed too: evidence, not a confirmation
        return f"{FIXES[mechanism]}: with {near[0]} it reaches the top k (another stage differs too)"
    if tried:
        return f"{FIXES[mechanism]}; measured here, and it misses the top k there too: {', '.join(tried)}"
    return f"{FIXES[mechanism]} (not measured: `ragcourt rank DOCS {flag} …` would measure it)"


def _changed(chosen: PipelineSpec, other: PipelineSpec, fields: tuple[str, ...]) -> list[str]:
    """The stages that differ, the blamed ones first; the embedder is left out when one side has none
    (BM25 uses no embedder, so BM25 against dense is a change of retriever alone)."""
    changed = chosen.differs_only_in(other)
    if chosen.embedder is None or other.embedder is None:
        changed = [name for name in changed if name != "embedder"]
    return sorted(changed, key=lambda name: name not in fields)


def _hits(evaluation: Evaluation, question: str) -> bool:
    result = evaluation.results.get(question)
    return result is not None and result.metrics["hit_at_k"] == 1.0


def _no_embedder_finds(question: str, measured: list[Evaluation]) -> bool:
    results = [
        evaluation.results.get(question) for evaluation in measured if evaluation.spec.retriever == "dense"
    ]
    return all(result is None or result.metrics["hit_at_k"] == 0.0 for result in results)
