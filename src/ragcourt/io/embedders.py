"""Turning a name from the configuration or a flag into an ``Embedder`` (design §7.3, §11.4).

``nomic-embed-text`` is an Ollama model; ``endpoint:openai/text-embedding-3-small`` an endpoint model;
the name of a registered embedder stage (with ``:key=value`` parameters) is that stage. A stage that
takes a ``client`` parameter is given the one client.
"""

from __future__ import annotations

import inspect
from collections.abc import Mapping

from ragcourt import stages
from ragcourt.io.client import ENDPOINT_PREFIX
from ragcourt.stages.specs import check_params, parse_spec
from ragcourt.types import Embedder, ModelClient


def make_embedder(name: str, client: ModelClient) -> Embedder:
    """The embedder ``name`` stands for, built with the client where it needs one."""
    if name.startswith(ENDPOINT_PREFIX):
        return _build("endpoint", {"model": name}, client)
    if name.split(":", maxsplit=1)[0] not in stages.names("embedder"):
        return _build("ollama", {"model": name}, client)  # a model name, tag included: qwen3-embedding:0.6b
    spec = parse_spec(name)
    check_params(stages.find("embedder", spec.name).function, spec, injected=("client",))
    return _build(spec.name, spec.kwargs(), client)


def _build(stage_name: str, params: Mapping[str, object], client: ModelClient) -> Embedder:
    factory = stages.find("embedder", stage_name).function
    if "client" in inspect.signature(factory).parameters:
        params = {**params, "client": client}
    built: Embedder = factory(**params)
    return built
