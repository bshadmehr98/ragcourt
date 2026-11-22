"""The ``openai`` dialect of the one client: any OpenAI-compatible endpoint (design §11.1).

Chat completions, embeddings and the ``/rerank`` route of llama.cpp, vLLM, TEI, Jina and Cohere. The key
is read from the environment variable the configuration names, sent only in a header, never written.
"""

from __future__ import annotations

import os

from ragcourt.errors import ConfigError
from ragcourt.io.http import Sleep, request_json
from ragcourt.io.replies import clean_reply
from ragcourt.types import ChatRequest, Embedded, ModelInfo
from ragcourt.types.config import Endpoint

BATCH = 64


class OpenAICompatible:
    """Talks to one configured endpoint."""

    def __init__(self, endpoint: Endpoint, sleep: Sleep) -> None:
        self.endpoint = endpoint
        self.sleep = sleep

    def _headers(self) -> dict[str, str]:
        name = self.endpoint.api_key_env
        if not name:
            return {}
        key = os.environ.get(name)
        if not key:
            raise ConfigError(
                f"Endpoint {self.endpoint.name!r} reads its key from ${name}, which is not set."
            )
        return {"Authorization": f"Bearer {key}"}

    def chat(self, request: ChatRequest) -> str:
        """The first choice's text."""
        body = {
            "model": request.model,
            "messages": [{"role": "user", "content": request.prompt}],
            "temperature": request.temperature,
            "seed": request.seed,
        }
        reply = request_json(
            f"{self.endpoint.base_url}/chat/completions", body, headers=self._headers(), sleep=self.sleep
        )
        return clean_reply(str(reply["choices"][0]["message"]["content"]))

    def embed(self, model: str, texts: list[str]) -> Embedded:
        """Vectors in batches; per-text token counts are not reported, so sizes are estimated."""
        vectors: list[list[float]] = []
        for first in range(0, len(texts), BATCH):
            body = {"model": model, "input": texts[first : first + BATCH]}
            reply = request_json(
                f"{self.endpoint.base_url}/embeddings", body, headers=self._headers(), sleep=self.sleep
            )
            ordered = sorted(reply["data"], key=lambda item: item["index"])
            for item in ordered:
                vectors.append([float(value) for value in item["embedding"]])
        return Embedded(vectors, None)

    def show(self, model: str) -> ModelInfo:
        """Endpoints do not say a model's input limit; it is unknown unless configured."""
        return ModelInfo(model)

    def rerank(self, model: str, query: str, documents: list[str]) -> list[float]:
        """One score per document from ``/rerank`` (Jina and Cohere format)."""
        body = {"model": model, "query": query, "documents": documents}
        reply = request_json(
            f"{self.endpoint.base_url}/rerank", body, headers=self._headers(), sleep=self.sleep
        )
        scores = [0.0] * len(documents)
        for item in reply["results"]:
            scores[int(item["index"])] = float(item["relevance_score"])
        return scores
