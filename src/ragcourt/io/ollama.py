"""The ``ollama`` dialect of the one client: Ollama's own API on this machine (design §11.1, D-041).

Embeddings go one text per call, so the token count Ollama reports is that text's, with ``num_ctx`` and
``num_batch`` set to the model's context length so the model reads all it can. Chat asks for JSON with
thinking off and a fixed seed.
"""

from __future__ import annotations

from typing import Any

from ragcourt.io.http import Sleep, request_json, stream_json_lines
from ragcourt.io.replies import clean_reply
from ragcourt.types import ChatRequest, Embedded, ModelInfo


class Ollama:
    """Talks to one Ollama server; remembers what ``/api/show`` said about each model."""

    def __init__(self, url: str, sleep: Sleep) -> None:
        self.url = url
        self.sleep = sleep
        self.shown: dict[str, ModelInfo] = {}

    def chat(self, request: ChatRequest) -> str:
        """The model's reply, with reasoning blocks removed."""
        body: dict[str, Any] = {
            "model": request.model,
            "messages": [{"role": "user", "content": request.prompt}],
            "stream": False,
            "think": False,
            "options": {"temperature": request.temperature, "seed": request.seed},
        }
        if request.json_reply:
            body["format"] = "json"
        reply = request_json(f"{self.url}/api/chat", body, sleep=self.sleep)
        return clean_reply(str(reply.get("message", {}).get("content", "")))

    def embed(self, model: str, texts: list[str]) -> Embedded:
        """One call per text: the vector and that text's token count."""
        context = self.show(model).context_length
        options = {"num_ctx": context, "num_batch": context} if context else {}
        vectors: list[list[float]] = []
        counts: list[int] = []
        for text in texts:
            body = {"model": model, "input": [text], "options": options}
            reply = request_json(f"{self.url}/api/embed", body, sleep=self.sleep)
            vectors.append([float(value) for value in reply["embeddings"][0]])
            counts.append(int(reply.get("prompt_eval_count", 0)))
        return Embedded(vectors, counts)

    def show(self, model: str) -> ModelInfo:
        """The model's context length, size and digest, asked once per model."""
        if model not in self.shown:
            reply = request_json(f"{self.url}/api/show", {"model": model}, sleep=self.sleep)
            info = reply.get("model_info", {})
            lengths = [int(value) for key, value in info.items() if key.endswith(".context_length")]
            details = self.installed().get(model)
            size, digest = (details.size_bytes, details.digest) if details else (None, None)
            self.shown[model] = ModelInfo(model, lengths[0] if lengths else None, size, digest)
        return self.shown[model]

    def installed(self) -> dict[str, ModelInfo]:
        """The models Ollama has, by name (with and without ``:latest``)."""
        reply = request_json(f"{self.url}/api/tags", sleep=self.sleep)
        models: dict[str, ModelInfo] = {}
        for entry in reply.get("models", []):
            info = ModelInfo(entry["name"], None, entry.get("size"), entry.get("digest"))
            models[entry["name"]] = info
            models[entry["name"].removesuffix(":latest")] = info
        return models

    def pull(self, model: str) -> None:
        """Download a model; only ``setup`` and ``models set`` call this, after the user agreed."""
        stream_json_lines(f"{self.url}/api/pull", {"model": model, "stream": True})

    def hardware(self) -> dict[str, int]:
        """The memory of the models loaded now, as Ollama reports it (``/api/ps``)."""
        reply = request_json(f"{self.url}/api/ps", sleep=self.sleep)
        loaded = reply.get("models", [])
        return {"loaded_vram": sum(int(model.get("size_vram", 0)) for model in loaded)}
