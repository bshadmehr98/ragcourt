"""The ``ragcourt.toml`` that ``setup`` writes: every role on its own line under a comment (D-031)."""

from __future__ import annotations

from ragcourt.io.toml_edit import toml_value

TEMPLATE = """# ragcourt settings. Every line is optional; delete one to get the default back.
# Change a model with `ragcourt models set ROLE MODEL`, or edit the line. See docs/models.md.

[models]
# writer: writes test questions and copies a quote that answers each.
writer = {writer}
# judge: drops invalid questions and those answerable without your documents (self-tested first).
judge = {judge}
# embedders: the embedding models ranked against each other on your documents.
embedders = {embedders}
# reranker: the chat model of the llm reranker, which orders the top 20 candidates.
reranker = {reranker}
# doctor: describes your documents and suggests (or writes) a chunker.
doctor = {doctor}
"""


def config_text(roles: dict[str, tuple[str, ...]]) -> str:
    """The commented configuration for these models."""
    values = {role: toml_value(models, as_list=role == "embedders") for role, models in roles.items()}
    return TEMPLATE.format(**values)
