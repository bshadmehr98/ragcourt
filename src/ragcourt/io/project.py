"""Opening a project for a command: its settings, its stages, its working folder and the client.

The project is the current folder: ``ragcourt.toml`` and ``ragcourt_stages/`` live there, and everything
ragcourt writes goes in ``.ragcourt/`` there unless ``--workdir`` says otherwise (design §3.3).
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

from ragcourt import stages
from ragcourt.errors import EndpointError
from ragcourt.io.cache import CachedEmbedder, EmbeddingStore, identity_of
from ragcourt.io.client import Client
from ragcourt.io.config import load_config
from ragcourt.io.embedders import make_embedder
from ragcourt.types import ChatRequest, Embedder
from ragcourt.types.config import Config, Role

WORKDIR = ".ragcourt"
# How a command adds its parser: ``subparsers.add_parser`` of the command line.
AddParser = Callable[..., argparse.ArgumentParser]


@dataclass(frozen=True)
class ProjectOptions:
    """What the common flags of every command say."""

    project: Path
    config_file: Path | None = None
    stages_dir: Path | None = None
    workdir: Path | None = None
    seed: int | None = None


@dataclass(frozen=True)
class Project:
    """A command's view of the project."""

    config: Config
    workdir: Path
    client: Client
    user_stage_files: tuple[Path, ...]

    def embedder(self, name: str) -> Embedder:
        """The embedder ``name``, behind the embedding cache."""
        built = make_embedder(name, self.client, self.workdir / "cache" / "limits.json")
        store = EmbeddingStore.open(self.workdir / "cache" / "embeddings", identity_of(built))
        return CachedEmbedder(built, store)

    def role(self, name: str, flag: str | None = None) -> Role:
        """A role's models: the flag for this run, else ``ragcourt.toml``, else the default (D-031)."""
        if flag:
            return Role(name, tuple(part.strip() for part in flag.split(",") if part.strip()), "flag")
        return self.config.role(name)

    def chat(self, model: str, *, json_reply: bool = True) -> Callable[[str], str]:
        """A prompt-in, reply-out function for ``model``, with the run's seed."""

        def ask(prompt: str) -> str:
            return self.client.chat(ChatRequest(model, prompt, json_reply, 0.0, self.config.seed))

        return ask

    def user_stage_names(self, kind: str) -> list[str]:
        """The names of the user's own stages of one kind."""
        folders = {path.resolve() for path in self.user_stage_files}
        return [
            name for name in stages.names(kind) if Path(stages.find(kind, name).file).resolve() in folders
        ]


def open_project(options: ProjectOptions) -> Project:
    """Read the settings, load the built-in and the user's stages, and make the client."""
    config = load_config(options.project, options.config_file)
    if options.seed is not None:
        config = replace(config, seed=options.seed)
    stages.load_builtins()
    folder = options.stages_dir or config.stage_folder()
    explicit = options.stages_dir is not None or config.stages_dir is not None
    files = stages.load_folder(folder) if folder.is_dir() or explicit else []
    workdir = options.workdir or options.project / WORKDIR
    return Project(config, workdir, Client(config), tuple(files))


def try_embedder(project: Project, name: str) -> tuple[Embedder | None, str]:
    """The embedder, or None with the reason when its server does not answer (the caller estimates)."""
    try:
        return project.embedder(name), ""
    except EndpointError as error:
        return None, str(error)
