"""The embedding cache, in plain files (design §10.2, D-016).

One folder per embedder identity under ``.ragcourt/cache/embeddings/``: ``model.json`` (the identity, the
dimension, the cache version), ``keys.txt`` (one ``sha256 token_count`` line per text) and ``vectors.f32``
(float32 vectors in the same order). Both files are only appended to, the vector before its key, so a
torn last write leaves a vector without a key, which loading trims. A cached text is never sent again.
"""

from __future__ import annotations

import array
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from ragcourt.types import Embedded, Embedder, Vector

CACHE_VERSION = 1
UNKNOWN_COUNT = -1


def identity_of(embedder: Embedder) -> str:
    """What makes two embedders give the same vectors: the model and its settings, never the client."""
    settings = vars(embedder) if hasattr(embedder, "__dict__") else {}
    parts = [
        f"{key}={value}" for key, value in sorted(settings.items()) if isinstance(value, str | int | float)
    ]
    return "|".join([embedder.model, *parts])


def text_key(text: str, *, as_query: bool) -> str:
    """The cache key of a text: its SHA-256, separately for questions and chunks."""
    return hashlib.sha256(("q\0" if as_query else "d\0").encode() + text.encode("utf-8")).hexdigest()


@dataclass
class EmbeddingStore:
    """One identity's cache folder, read whole into memory."""

    folder: Path
    vectors: dict[str, tuple[Vector, int]] = field(default_factory=dict[str, tuple[Vector, int]])
    dimension: int = 0

    @classmethod
    def open(cls, root: Path, identity: str) -> EmbeddingStore:
        """The folder for ``identity`` under ``root``, loaded; created when first written."""
        digest = hashlib.sha256(f"{CACHE_VERSION}:{identity}".encode()).hexdigest()[:16]
        slug = "".join(char if char.isalnum() else "-" for char in identity.split("|", maxsplit=1)[0])[:40]
        store = cls(root / f"{slug}-{digest}")
        store._load(identity)
        return store

    def _load(self, identity: str) -> None:
        meta = self.folder / "model.json"
        if not meta.is_file():
            self.folder.mkdir(parents=True, exist_ok=True)
            meta.write_text(json.dumps({"identity": identity, "version": CACHE_VERSION}) + "\n")
            return
        self.dimension = int(json.loads(meta.read_text()).get("dimension", 0))
        keys_file, vectors_file = self.folder / "keys.txt", self.folder / "vectors.f32"
        if not self.dimension or not keys_file.is_file() or not vectors_file.is_file():
            return
        values = array.array("f")
        values.frombytes(vectors_file.read_bytes())
        lines = keys_file.read_text().split("\n")[:-1]
        for number, line in enumerate(lines[: len(values) // self.dimension]):
            key, count = line.split(" ")
            row = values[number * self.dimension : (number + 1) * self.dimension]
            self.vectors[key] = (list(row), int(count))

    def add(self, key: str, vector: Vector, count: int | None) -> None:
        """Append one vector, then its key."""
        if not self.dimension:
            self.dimension = len(vector)
            meta = self.folder / "model.json"
            data = json.loads(meta.read_text())
            meta.write_text(json.dumps({**data, "dimension": self.dimension}) + "\n")
        with (self.folder / "vectors.f32").open("ab") as handle:
            handle.write(array.array("f", vector).tobytes())
        with (self.folder / "keys.txt").open("a") as handle:
            handle.write(f"{key} {UNKNOWN_COUNT if count is None else count}\n")
        self.vectors[key] = (list(array.array("f", vector)), UNKNOWN_COUNT if count is None else count)


@dataclass
class CachedEmbedder:
    """Implements ``Embedder``: answers from the store, embeds only what is missing, counts the calls."""

    inner: Embedder
    store: EmbeddingStore
    calls: int = 0
    texts_embedded: int = 0

    @property
    def model(self) -> str:
        """The inner embedder's model."""
        return self.inner.model

    @property
    def max_tokens(self) -> int | None:
        """The inner embedder's limit in force."""
        return self.inner.max_tokens

    @property
    def tokenizer(self) -> str:
        """How the inner embedder counts tokens."""
        return self.inner.tokenizer

    def embed(self, texts: list[str], *, as_query: bool = False) -> Embedded:
        """Vectors and counts for ``texts``, embedding only those not cached."""
        keys = [text_key(text, as_query=as_query) for text in texts]
        missing = sorted(
            {
                key: text for key, text in zip(keys, texts, strict=True) if key not in self.store.vectors
            }.items()
        )
        if missing:
            fresh = self.inner.embed([text for _, text in missing], as_query=as_query)
            self.calls += 1
            self.texts_embedded += len(missing)
            counts = fresh.token_counts or [None] * len(missing)
            for (key, _), vector, count in zip(missing, fresh.vectors, counts, strict=True):
                self.store.add(key, vector, count)
        rows = [self.store.vectors[key] for key in keys]
        counts_known = all(count != UNKNOWN_COUNT for _, count in rows)
        return Embedded(
            [vector for vector, _ in rows], [count for _, count in rows] if counts_known else None
        )
