"""Loading stages: the built-ins and the user's own folder (design §7.2).

The built-ins live one per file in ``stages/<kind>s/`` and are found by listing those folders, so adding
one is adding a file. The user's own are every ``.py`` file of their ``ragcourt_stages/`` folder (hidden
files left out), imported in sorted order as the modules ``ragcourt_stages.<name>``, so one file can
import a helper from another (``from ragcourt_stages import helpers``). This is the one place ragcourt
imports code by name (CONTRIBUTING.md rule 5).
"""

from __future__ import annotations

import importlib
import importlib.util
import pkgutil
import sys
import types
from pathlib import Path

from ragcourt.errors import ConfigError, RagCourtError

USER_PACKAGE = "ragcourt_stages"
BUILTIN_PACKAGES = ("chunkers", "embedders", "retrievers", "rerankers")


def load_builtins() -> list[str]:
    """Import every built-in stage file; return the modules. Importing twice does nothing."""
    loaded: list[str] = []
    for kind_package in BUILTIN_PACKAGES:
        package = importlib.import_module(f"ragcourt.stages.{kind_package}")
        for module in sorted(pkgutil.iter_modules(package.__path__), key=lambda info: info.name):
            loaded.append(importlib.import_module(f"{package.__name__}.{module.name}").__name__)
    return loaded


def load_folder(folder: Path) -> list[Path]:
    """Import every ``.py`` file in the user's stage folder, in sorted order; return the files loaded."""
    if not folder.is_dir():
        raise ConfigError(f"The stage folder {folder} does not exist. Create it or pass --stages DIR.")
    folder = folder.resolve()
    parent = types.ModuleType(USER_PACKAGE)
    parent.__path__ = [str(folder)]
    sys.modules[USER_PACKAGE] = parent
    files = sorted(path for path in folder.glob("*.py") if not path.name.startswith("."))
    for path in files:
        _load_file(path)
    return files


def _load_file(path: Path) -> None:
    module_name = f"{USER_PACKAGE}.{path.stem}"
    already = sys.modules.get(module_name)
    if already is not None and getattr(already, "__file__", None) == str(path):
        return  # imported already, by an earlier file of the folder or an earlier load
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ConfigError(f"{path} cannot be imported as Python. Check its name and contents.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except RagCourtError:
        del sys.modules[module_name]
        raise  # a duplicate name already says what to do
    except Exception as error:
        del sys.modules[module_name]
        raise ConfigError(f"Loading your stage file {path} failed: {error!r}. Fix the file.") from error
