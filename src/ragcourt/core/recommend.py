"""Which local models to recommend for a machine (design §11.3, D-027).

The table is justified by measurement on the owner's machine (design/history/0002-local-models.md): gemma4
quoted verbatim 19 times in 20 and judged strictly; smaller chat models quoted less and passed refusals as
correct. Embedders are small enough for any machine.
"""

from __future__ import annotations

from dataclasses import dataclass

EMBEDDERS: tuple[str, ...] = ("nomic-embed-text", "embeddinggemma", "mxbai-embed-large")
# Installed sizes in GB, as measured (history 0002).
SIZES_GB = {
    "gemma4": 6.6,
    "qwen3:4b": 2.5,
    "llama3.2:3b": 2.0,
    "nomic-embed-text": 0.27,
    "embeddinggemma": 0.62,
    "mxbai-embed-large": 0.67,
    "bge-m3": 1.2,
    "all-minilm": 0.05,
    "qwen3-embedding:0.6b": 0.64,
}


@dataclass(frozen=True)
class Recommendation:
    """Models per role for this machine, and why."""

    roles: dict[str, tuple[str, ...]]
    why: str


def recommend(ram_gb: float, vram_gb: float | None) -> Recommendation:
    """The models that fit: gemma4 when it fits in GPU memory or plenty of RAM, else a smaller chat model."""
    if vram_gb is not None and vram_gb >= 7:
        chat, why = (
            "gemma4",
            f"{vram_gb:.0f} GB of GPU memory fits gemma4, the best measured writer and judge",
        )
    elif ram_gb >= 16:
        chat, why = "gemma4", f"no large GPU, but {ram_gb:.0f} GB of RAM runs gemma4 on the CPU (slowly)"
    else:
        chat, why = "qwen3:4b", f"{ram_gb:.0f} GB of RAM: qwen3:4b fits; check its judge self-test"
    roles = {
        "writer": (chat,),
        "judge": (chat,),
        "embedders": EMBEDDERS,
        "reranker": (chat,),
        "doctor": (chat,),
    }
    return Recommendation(roles, why)
