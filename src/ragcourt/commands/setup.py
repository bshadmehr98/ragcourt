"""``ragcourt setup``: once per machine, pick local models that fit, pull them if you agree (§11.3).

Checks that Ollama answers, reads how much memory the machine has, recommends models, shows their sizes,
pulls the missing ones only after your yes (or ``--yes``), writes a commented ``ragcourt.toml`` when there is
none, and runs the judge's self-test case by case.
"""

from __future__ import annotations

import argparse

from ragcourt.core.recommend import SIZES_GB, recommend
from ragcourt.flows.judge import check_judge
from ragcourt.io.ask import confirm
from ragcourt.io.config import CONFIG_FILE
from ragcourt.io.config_template import config_text
from ragcourt.io.machine import gpu_gb, ram_gb
from ragcourt.io.project import AddParser, Project, ProjectOptions, open_project
from ragcourt.io.prompts import load_prompts
from ragcourt.io.terminal import table

NAME = "setup"
HELP = "once per machine: check Ollama, recommend models that fit, pull them after you agree"
OLLAMA_HELP = (
    "Install Ollama from https://ollama.com, start it (`ollama serve`), then run `ragcourt setup` again."
)


def register(add_parser: AddParser, common: argparse.ArgumentParser) -> None:
    """Add ``setup``."""
    parser = add_parser(NAME, help=HELP, description=__doc__, parents=[common])
    parser.add_argument("--yes", action="store_true", help="pull the missing models without asking")
    parser.set_defaults(run=run)


def run(args: argparse.Namespace) -> int:
    """Check, recommend, pull with consent, configure, self-test."""
    project = open_project(args.options)
    if not project.client.ollama_answers():
        print(f"Ollama does not answer at {project.config.ollama_url}. {OLLAMA_HELP}")
        return 1
    advice = recommend(ram_gb(), gpu_gb())
    print(f"Recommended for this machine: {advice.why}.")
    installed = project.client.ollama.installed()
    models: list[str] = []
    for chosen in advice.roles.values():
        models += [model for model in chosen if model not in models]
    rows = [[model, "yes" if model in installed else "no", _size(model)] for model in models]
    print(table(["model", "installed", "size"], rows))
    missing = [model for model in models if model not in installed]
    if missing and not _pull(project, missing, yes=args.yes):
        return 0
    _write_config(project, advice.roles)
    judge = open_project(ProjectOptions(project.config.project, None, None, project.workdir)).role("judge")
    templates = {name: prompt.text for name, prompt in load_prompts(project.config.prompts_dir).items()}
    check_judge(project, judge.models[0], templates, print)
    print("\nReady. Next: `ragcourt audit DOCS` (seconds), then `ragcourt rank DOCS` (shows its plan first).")
    return 0


def _size(model: str) -> str:
    size = SIZES_GB.get(model)
    return f"{size:.2f} GB" if size is not None else "unknown"


def _pull(project: Project, missing: list[str], *, yes: bool) -> bool:
    total = sum(SIZES_GB.get(model, 0.0) for model in missing)
    if not confirm(f"Download {len(missing)} models ({total:.1f} GB): {', '.join(missing)}?", yes=yes):
        print("Nothing downloaded. Pull them with `ollama pull MODEL`, or name others in ragcourt.toml.")
        return False
    for model in missing:
        print(f"Pulling {model} …")
        project.client.ollama.pull(model)
    return True


def _write_config(project: Project, roles: dict[str, tuple[str, ...]]) -> None:
    path = project.config.project / CONFIG_FILE
    if path.exists():
        print(f"{path} exists; left as it is. Change a model with `ragcourt models set ROLE MODEL`.")
        return
    path.write_text(config_text(roles), encoding="utf-8")
    print(f"Wrote {path}: one line per role, each under a comment saying what it does.")
