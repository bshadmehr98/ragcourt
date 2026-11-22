"""``ragcourt models``: see which model does each job and change one (design §11.4, D-031).

``ragcourt models`` shows each role, its model, where the choice came from, whether it is installed, and the
judge's self-test; ``models set ROLE MODEL`` writes ``ragcourt.toml`` keeping its comments (a new judge is
self-tested at once); ``models test judge`` runs the self-test again, case by case.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping

from ragcourt.core.recommend import SIZES_GB
from ragcourt.errors import ConfigError
from ragcourt.flows.judge import JUDGE_PROMPTS, check_judge
from ragcourt.io.ask import confirm
from ragcourt.io.config import CONFIG_FILE
from ragcourt.io.judge_record import load_selftest, record_path
from ragcourt.io.narration import source_words
from ragcourt.io.project import AddParser, Project, ProjectOptions, open_project
from ragcourt.io.prompts import load_prompts
from ragcourt.io.question_file import text_hash
from ragcourt.io.terminal import table
from ragcourt.io.toml_edit import set_role, toml_value
from ragcourt.types.config import ROLES

NAME = "models"
HELP = "show the model of each role, `models set ROLE MODEL` to change one, `models test judge`"


def register(add_parser: AddParser, common: argparse.ArgumentParser) -> None:
    """Add ``models``."""
    parser = add_parser(NAME, help=HELP, description=__doc__, parents=[common])
    parser.add_argument("action", nargs="?", choices=["set", "test"], help="set a role, or test the judge")
    parser.add_argument("role", nargs="?", help="writer, judge, embedders, reranker or doctor")
    parser.add_argument("model", nargs="?", help="a model, or several separated by commas for embedders")
    parser.add_argument("--yes", action="store_true", help="pull a missing model without asking")
    parser.set_defaults(run=run)


def run(args: argparse.Namespace) -> int:
    """Show, set or test."""
    project = open_project(args.options)
    if args.action == "set":
        return _set(project, args.role, args.model, yes=args.yes)
    if args.action == "test":
        return _test(project, args.role)
    print(roles_table(project))
    return 0


def roles_table(project: Project) -> str:
    """Each role with its model, origin, installation, size and (for the judge) self-test."""
    installed = project.client.ollama.installed() if project.client.ollama_answers() else None
    rows: list[list[object]] = []
    for name in ROLES:
        role = project.role(name)
        for model in role.models:
            rows.append(
                [
                    name,
                    model,
                    source_words(role),
                    _installed(model, installed),
                    _size(model),
                    _tested(project, name, model),
                ]
            )
    return table(["role", "model", "chosen by", "installed", "size", "self-test"], rows)


def _installed(model: str, installed: Mapping[str, object] | None) -> str:
    if model.startswith("endpoint:"):
        return "endpoint"
    if installed is None:
        return "unknown (Ollama not answering)"
    return "yes" if model in installed else "no"


def _size(model: str) -> str:
    size = SIZES_GB.get(model)
    return f"{size:.1f} GB" if size is not None else "unknown"


def _tested(project: Project, role: str, model: str) -> str:
    if role != "judge":
        return ""
    prompts = load_prompts(project.config.prompts_dir)
    test = load_selftest(project.workdir, model, {name: prompts[name].hash for name in JUDGE_PROMPTS})
    return "not run" if test is None else f"{test.score:.0%} ({'passed' if test.passed else 'FAILED'})"


def _set(project: Project, role: str | None, model: str | None, *, yes: bool) -> int:
    if role not in ROLES or not model:
        raise ConfigError(f"Write `ragcourt models set ROLE MODEL` with ROLE one of {', '.join(ROLES)}.")
    models = tuple(part.strip() for part in model.split(",") if part.strip())
    for name in models:  # every model is there before ragcourt.toml names it
        _ensure_installed(project, name, yes=yes)
    path = project.config.file or project.config.project / CONFIG_FILE
    set_role(path, role, toml_value(models, as_list=role == "embedders"))
    print(f"{role} = {', '.join(models)} (written to {path})")
    if role == "judge":
        refreshed = open_project_like(project)
        templates = {name: prompt.text for name, prompt in load_prompts(refreshed.config.prompts_dir).items()}
        check_judge(refreshed, models[0], templates, print)
    return 0


def open_project_like(project: Project) -> Project:
    """The project read again, after its configuration changed."""
    return open_project(ProjectOptions(project.config.project, project.config.file, None, project.workdir))


def _ensure_installed(project: Project, model: str, *, yes: bool) -> None:
    if model.startswith("endpoint:"):
        return
    if not project.client.ollama_answers():
        raise ConfigError(f"Ollama does not answer at {project.config.ollama_url}; nothing was changed.")
    if model in project.client.ollama.installed():
        return
    if not confirm(f"{model} is not installed ({_size(model)}). Pull it now?", yes=yes):
        raise ConfigError(
            f"{model} is not installed; nothing was changed. `ollama pull {model}` installs it."
        )
    print(f"Pulling {model} …")
    project.client.ollama.pull(model)


def _test(project: Project, role: str | None) -> int:
    if role != "judge":
        raise ConfigError("Only the judge has a self-test: `ragcourt models test judge`.")
    model = project.role("judge").models[0]
    templates = {name: prompt.text for name, prompt in load_prompts(project.config.prompts_dir).items()}
    hashes = {name: text_hash(templates[name]) for name in JUDGE_PROMPTS}
    record_path(project.workdir, model, hashes).unlink(missing_ok=True)
    test = check_judge(project, model, templates, print)
    return 0 if test.passed else 1
