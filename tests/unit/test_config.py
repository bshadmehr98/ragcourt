"""Reading ragcourt.toml (design §3.3, D-039)."""

from pathlib import Path

import pytest

from ragcourt import ConfigError, load_config


def test_no_file_means_the_defaults(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    assert config.file is None
    assert config.stages_dir == tmp_path / "ragcourt_stages"


def test_the_file_sets_the_stage_folder(tmp_path: Path) -> None:
    (tmp_path / "ragcourt.toml").write_text('stages_dir = "my_stages"\n')
    config = load_config(tmp_path)
    assert config.file == tmp_path / "ragcourt.toml"
    assert config.stages_dir == tmp_path / "my_stages"


def test_an_empty_file_means_the_defaults(tmp_path: Path) -> None:
    (tmp_path / "ragcourt.toml").write_text("")
    assert load_config(tmp_path).stages_dir == tmp_path / "ragcourt_stages"


def test_an_unknown_key_is_an_error_that_lists_the_known_ones(tmp_path: Path) -> None:
    (tmp_path / "ragcourt.toml").write_text('stage_dir = "typo"\n')
    with pytest.raises(ConfigError, match=r"unknown setting stage_dir\. The settings are: stages_dir"):
        load_config(tmp_path)


@pytest.mark.parametrize("value", ["3", '""', "[]"])
def test_a_wrong_type_names_the_key(tmp_path: Path, value: str) -> None:
    (tmp_path / "ragcourt.toml").write_text(f"stages_dir = {value}\n")
    with pytest.raises(ConfigError, match="stages_dir must be a non-empty string"):
        load_config(tmp_path)


def test_invalid_toml_names_the_file(tmp_path: Path) -> None:
    (tmp_path / "ragcourt.toml").write_text("stages_dir = \n")
    with pytest.raises(ConfigError, match="is not valid TOML"):
        load_config(tmp_path)
