"""The one client for every model (design §11.1): Ollama by default, configured endpoints by name.

A model named ``endpoint:<name>/<model>`` goes to the endpoint ``<name>`` of ``ragcourt.toml``; any other
name is an Ollama model on this machine. Nothing else is ever contacted (design §11.2).
"""

from __future__ import annotations

import time

from ragcourt.errors import ConfigError, EndpointError
from ragcourt.io.http import Sleep
from ragcourt.io.ollama import Ollama
from ragcourt.io.openai_compat import OpenAICompatible
from ragcourt.types import ChatRequest, Embedded, ModelInfo
from ragcourt.types.config import Config

ENDPOINT_PREFIX = "endpoint:"


class Client:
    """Implements ``ModelClient``: routes each call to Ollama or to the named endpoint."""

    def __init__(self, config: Config, sleep: Sleep = time.sleep) -> None:
        self.ollama = Ollama(config.ollama_url, sleep)
        self.endpoints = {
            name: OpenAICompatible(endpoint, sleep) for name, endpoint in config.endpoints.items()
        }

    def _route(self, model: str) -> tuple[Ollama | OpenAICompatible, str]:
        if not model.startswith(ENDPOINT_PREFIX):
            return self.ollama, model
        name, slash, model_name = model.removeprefix(ENDPOINT_PREFIX).partition("/")
        if not slash or name not in self.endpoints:
            known = ", ".join(sorted(self.endpoints)) or "none configured"
            raise ConfigError(
                f"{model!r} names no configured endpoint (endpoints: {known}); see [endpoints]."
            )
        return self.endpoints[name], model_name

    def chat(self, request: ChatRequest) -> str:
        """The model's reply as text."""
        server, model = self._route(request.model)
        return server.chat(
            ChatRequest(model, request.prompt, request.json_reply, request.temperature, request.seed)
        )

    def embed(self, model: str, texts: list[str]) -> Embedded:
        """Vectors and, where the server reports them, token counts."""
        server, name = self._route(model)
        return server.embed(name, texts)

    def show(self, model: str) -> ModelInfo:
        """The model's input limit, size and digest, where known."""
        server, name = self._route(model)
        return server.show(name)

    def rerank(self, model: str, query: str, documents: list[str]) -> list[float]:
        """Scores from an endpoint's ``/rerank``; Ollama has no such route (D-015)."""
        server, name = self._route(model)
        if isinstance(server, Ollama):
            raise ConfigError(
                f"Ollama has no rerank route; name an endpoint model for {model!r}, or use the llm reranker."
            )
        return server.rerank(name, query, documents)

    def ollama_answers(self) -> bool:
        """True when Ollama answers on its address."""
        try:
            self.ollama.installed()
        except EndpointError:
            return False
        return True
