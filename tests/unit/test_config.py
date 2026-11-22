"""Reading ragcourt.toml (design §3.3, D-039)."""

import os
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


@pytest.mark.parametrize("value", ["3", '""', '"   "', "[]"])
def test_a_wrong_type_names_the_key(tmp_path: Path, value: str) -> None:
    (tmp_path / "ragcourt.toml").write_text(f"stages_dir = {value}\n")
    with pytest.raises(ConfigError, match="stages_dir must be a non-empty string"):
        load_config(tmp_path)


def test_invalid_toml_names_the_file(tmp_path: Path) -> None:
    (tmp_path / "ragcourt.toml").write_text("stages_dir = \n")
    with pytest.raises(ConfigError, match="is not valid TOML"):
        load_config(tmp_path)


def test_an_absolute_stage_folder_is_kept(tmp_path: Path) -> None:
    elsewhere = tmp_path / "shared" / "stages"
    (tmp_path / "ragcourt.toml").write_text(f'stages_dir = "{elsewhere.as_posix()}"\n')
    assert load_config(tmp_path).stages_dir == elsewhere


def test_a_byte_order_mark_is_accepted(tmp_path: Path) -> None:
    (tmp_path / "ragcourt.toml").write_bytes('﻿stages_dir = "s"\n'.encode())
    assert load_config(tmp_path).stages_dir == tmp_path / "s"


def test_a_file_that_is_not_utf8_says_so(tmp_path: Path) -> None:
    (tmp_path / "ragcourt.toml").write_bytes('stages_dir = "caf\xe9"\n'.encode("latin-1"))
    with pytest.raises(ConfigError, match="is not UTF-8"):
        load_config(tmp_path)


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads every file")
def test_a_file_that_cannot_be_read_says_so(tmp_path: Path) -> None:
    config = tmp_path / "ragcourt.toml"
    config.write_text('stages_dir = "s"\n')
    config.chmod(0)
    try:
        with pytest.raises(ConfigError, match="cannot be read"):
            load_config(tmp_path)
    finally:
        config.chmod(0o600)
