"""The stage registry and the user's stage folder (design §7.2)."""

from pathlib import Path

import pytest

from ragcourt import ConfigError, stages

pytestmark = pytest.mark.usefixtures("registry")

CHUNKER_FILE = """
from ragcourt.stages import chunker

@chunker("{name}")
def split(text: str) -> list[str]:
    return text.split("\\n\\n")
"""


def test_each_decorator_registers_its_kind() -> None:
    @stages.chunker("t_chunker")
    def a(text: str) -> list[str]:
        return [text]

    @stages.embedder("t_embedder")
    def b() -> None: ...

    @stages.retriever("t_retriever")
    def c() -> None: ...

    @stages.reranker("t_reranker")
    def d(query: str, candidates: list[str]) -> list[float]:
        return [0.0] * len(candidates)

    for kind, function in (("chunker", a), ("embedder", b), ("retriever", c), ("reranker", d)):
        stage = stages.find(kind, f"t_{kind}")
        assert stage.function is function
        assert stage.file == __file__
        assert f"t_{kind}" in stages.names(kind)
    assert a("x") == ["x"]  # the decorator returns the function unchanged


def test_an_unknown_kind_is_refused() -> None:
    with pytest.raises(ConfigError, match="Unknown stage kind 'splitter'"):
        stages.register("splitter", "x", len)


def test_an_unknown_name_lists_the_known_ones() -> None:
    def scores(query: str, candidates: list[str]) -> list[float]:
        return [0.0] * len(candidates)

    stages.register("reranker", "t_known", scores)
    with pytest.raises(ConfigError, match=r"No reranker is named 'nope'\. Known rerankers: .*t_known"):
        stages.find("reranker", "nope")


def test_registering_the_same_function_again_is_allowed() -> None:
    def split(text: str) -> list[str]:
        return [text]

    stages.register("chunker", "t_again", split)
    stages.register("chunker", "t_again", split)
    assert stages.find("chunker", "t_again").function is split


def test_two_functions_with_one_name_in_one_file_are_refused() -> None:
    def first(text: str) -> list[str]:
        return [text]

    def second(text: str) -> list[str]:
        return [text]

    stages.register("chunker", "t_twice", first)
    with pytest.raises(ConfigError, match="Two chunkers are named 't_twice'"):
        stages.register("chunker", "t_twice", second)


def test_the_user_folder_is_loaded_in_sorted_order(tmp_path: Path) -> None:
    (tmp_path / "b_second.py").write_text(CHUNKER_FILE.format(name="t_b"))
    (tmp_path / "a_first.py").write_text(CHUNKER_FILE.format(name="t_a"))
    (tmp_path / "notes.txt").write_text("not python")
    loaded = stages.load_folder(tmp_path)
    assert [path.name for path in loaded] == ["a_first.py", "b_second.py"]
    assert stages.find("chunker", "t_a").function("x\n\ny") == ["x", "y"]


def test_loading_the_same_folder_twice_is_allowed(tmp_path: Path) -> None:
    (tmp_path / "mine.py").write_text(CHUNKER_FILE.format(name="t_reload"))
    stages.load_folder(tmp_path)
    stages.load_folder(tmp_path)
    assert stages.find("chunker", "t_reload").file == str(tmp_path / "mine.py")


def test_a_missing_folder_says_how_to_fix_it(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="does not exist"):
        stages.load_folder(tmp_path / "ragcourt_stages")


def test_a_broken_stage_file_is_named(tmp_path: Path) -> None:
    (tmp_path / "broken.py").write_text("raise ValueError('oops')\n")
    with pytest.raises(ConfigError, match=r"Loading your stage file .*broken\.py failed: ValueError"):
        stages.load_folder(tmp_path)


def test_a_file_python_cannot_import_is_named(tmp_path: Path) -> None:
    (tmp_path / "odd.py").mkdir()  # a folder named like a file: no loader for it
    with pytest.raises(ConfigError, match=r"odd\.py"):
        stages.load_folder(tmp_path)


def test_builtins_load_twice_without_error() -> None:
    stages.load_builtins()
    stages.load_builtins()
