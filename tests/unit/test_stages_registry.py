"""The stage registry and the user's stage folder (design §7.2)."""

import functools
import sys
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
        assert (stage.file, stage.line) == (__file__, function.__code__.co_firstlineno)
        assert f"t_{kind}" in stages.names(kind)
    assert a("x") == ["x"]  # the decorator returns the function unchanged


@pytest.mark.parametrize("call", [lambda: stages.find("chunkers", "x"), lambda: stages.names("splitter")])
def test_an_unknown_kind_is_refused_everywhere(call) -> None:
    with pytest.raises(ConfigError, match="Unknown stage kind"):
        call()


def test_registering_an_unknown_kind_is_refused() -> None:
    with pytest.raises(ConfigError, match="Unknown stage kind 'splitter'"):
        stages.register("splitter", "x", lambda text: [text])


@pytest.mark.parametrize("name", ["", "a:size=1", "two words", "a,b", "-dash", "x="])
def test_names_that_would_break_a_stage_spec_are_refused(name: str) -> None:
    with pytest.raises(ConfigError, match="cannot name a chunker"):
        stages.register("chunker", name, lambda text: [text])


@pytest.mark.parametrize("name", ["t_plain", "t.chonkie.token", "t-by-paragraph", "t_v2_split"])
def test_ordinary_names_are_accepted(name: str) -> None:
    assert stages.register("chunker", name, lambda text: [text]).name == name


def test_only_functions_can_be_stages() -> None:
    with pytest.raises(ConfigError, match="is not a function"):
        stages.register("chunker", "t_partial", functools.partial(str.split, sep="\n"))


def test_an_unknown_name_lists_the_known_ones() -> None:
    def scores(query: str, candidates: list[str]) -> list[float]:
        return [0.0] * len(candidates)

    stages.register("reranker", "t_known", scores)
    with pytest.raises(ConfigError, match=r"No reranker is named 'nope'\. Known rerankers: .*t_known"):
        stages.find("reranker", "nope")


def test_registering_the_same_definition_again_is_allowed() -> None:
    def split(text: str) -> list[str]:
        return [text]

    stages.register("chunker", "t_again", split)
    stages.register("chunker", "t_again", split)
    assert stages.find("chunker", "t_again").function is split


def test_two_definitions_with_one_name_in_one_file_are_refused(tmp_path: Path) -> None:
    (tmp_path / "twice.py").write_text(CHUNKER_FILE.format(name="t_twice") * 2)
    with pytest.raises(
        ConfigError, match=r"Two chunkers are named 't_twice': one in .*twice\.py:4, one in .*twice\.py:10"
    ):
        stages.load_folder(tmp_path)


def test_the_user_folder_is_loaded_in_sorted_order(tmp_path: Path) -> None:
    (tmp_path / "a_first.py").write_text(CHUNKER_FILE.format(name="t_a"))
    # b_second runs only after a_first: it looks up the stage a_first registered.
    (tmp_path / "b_second.py").write_text("from ragcourt.stages import find\nfind('chunker', 't_a')\n")
    (tmp_path / "notes.txt").write_text("not python")
    (tmp_path / ".hidden.py").write_text("raise SystemExit('hidden files are not run')\n")
    loaded = stages.load_folder(tmp_path)
    assert [path.name for path in loaded] == ["a_first.py", "b_second.py"]
    assert stages.find("chunker", "t_a").function("x\n\ny") == ["x", "y"]


def test_a_stage_file_can_import_a_helper_from_its_folder(tmp_path: Path) -> None:
    (tmp_path / "helpers.py").write_text("def paragraphs(text):\n    return text.split('\\n\\n')\n")
    (tmp_path / "mine.py").write_text(
        "from ragcourt.stages import chunker\nfrom ragcourt_stages.helpers import paragraphs\n\n"
        "@chunker('t_helped')\ndef helped(text):\n    return paragraphs(text)\n"
    )
    stages.load_folder(tmp_path)
    assert stages.find("chunker", "t_helped").function("a\n\nb") == ["a", "b"]


def test_loading_the_same_folder_twice_runs_each_file_once(tmp_path: Path) -> None:
    (tmp_path / "mine.py").write_text(CHUNKER_FILE.format(name="t_reload") + "RUNS.append(1)\n")
    (tmp_path / "mine.py").write_text("RUNS = []\n" + (tmp_path / "mine.py").read_text())
    stages.load_folder(tmp_path)
    stages.load_folder(tmp_path)
    assert stages.find("chunker", "t_reload").file == str((tmp_path / "mine.py").resolve())
    assert sys.modules["ragcourt_stages.mine"].RUNS == [1]


def test_a_folder_reached_through_a_link_is_the_same_folder(tmp_path: Path) -> None:
    (tmp_path / "real").mkdir()
    (tmp_path / "real" / "mine.py").write_text(CHUNKER_FILE.format(name="t_linked"))
    (tmp_path / "link").symlink_to(tmp_path / "real", target_is_directory=True)
    stages.load_folder(tmp_path / "real")
    stages.load_folder(tmp_path / "link")
    assert stages.find("chunker", "t_linked").file == str((tmp_path / "real" / "mine.py").resolve())


def test_a_missing_folder_says_how_to_fix_it(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="does not exist"):
        stages.load_folder(tmp_path / "ragcourt_stages")


def test_a_broken_stage_file_is_named_and_forgotten(tmp_path: Path) -> None:
    (tmp_path / "broken.py").write_text("raise ValueError('oops')\n")
    with pytest.raises(ConfigError, match=r"Loading your stage file .*broken\.py failed: ValueError"):
        stages.load_folder(tmp_path)
    assert "ragcourt_stages.broken" not in sys.modules


def test_a_file_without_a_loader_is_named(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "odd.py").write_text("")
    monkeypatch.setattr("importlib.util.spec_from_file_location", lambda *args, **kwargs: None)
    with pytest.raises(ConfigError, match=r"odd\.py cannot be imported as Python"):
        stages.load_folder(tmp_path)


def test_builtins_are_imported_from_their_folders(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from ragcourt.stages import chunkers

    (tmp_path / "t_builtin.py").write_text(CHUNKER_FILE.format(name="t_builtin"))
    monkeypatch.setattr(chunkers, "__path__", [str(tmp_path)])
    assert "ragcourt.stages.chunkers.t_builtin" in stages.load_builtins()
    assert "ragcourt.stages.chunkers.t_builtin" in stages.load_builtins()  # twice: no error
    assert "t_builtin" in stages.names("chunker")
    del sys.modules["ragcourt.stages.chunkers.t_builtin"]
