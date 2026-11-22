"""An offline project for examples, docs and tests: a fake Ollama answering with scripted models (§15.2).

``with offline_project(folder):`` starts the fake server, writes a small ``ragcourt.toml`` that points at it
(the fake writer and judge, the ``fake-embed`` and ``fake`` embedders, few questions per category) and makes
``folder`` the current directory, so every ``ragcourt`` command runs without a model or a network.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from ragcourt import stages
from ragcourt.testing.fake_ollama import FakeOllamaState, fake_ollama
from ragcourt.testing.scripted_replies import ScriptedReplies

TOML = """ollama_url = "{url}"
[models]
writer = "fake-chat"
judge = "fake-chat"
embedders = ["fake-embed", "fake"]
reranker = "fake-chat"
doctor = "fake-chat"
[questions]
per_category = {per_category}
min_held_out = 2
[search]
chunkers = ["recursive:size=200,overlap=20", "fixed:size=60,overlap=0", "markdown:size=300,overlap=0"]
resamples = 300
"""


@contextmanager
def offline_project(
    folder: Path, replies: ScriptedReplies | None = None, per_category: int = 6
) -> Generator[FakeOllamaState]:
    """Run ragcourt in ``folder`` against a fake Ollama; yields the server's state (its requests)."""
    from ragcourt.testing import register_fakes  # noqa: PLC0415 (the package imports this module)

    stages.load_builtins()
    register_fakes()
    previous = Path.cwd()
    folder.mkdir(parents=True, exist_ok=True)
    with fake_ollama() as (url, state):
        state.reply = replies or ScriptedReplies()
        (folder / "ragcourt.toml").write_text(
            TOML.format(url=url, per_category=per_category), encoding="utf-8"
        )
        os.chdir(folder)
        try:
            yield state
        finally:
            os.chdir(previous)
