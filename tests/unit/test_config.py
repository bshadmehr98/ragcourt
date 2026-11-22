"""Reading ragcourt.toml (design §3.3, §11.4, D-039)."""

import os
from pathlib import Path

import pytest

from ragcourt import ConfigError, load_config
from ragcourt.types.config import DEFAULT_MODELS

FULL = """
stages_dir = "my_stages"
seed = 7
ollama_url = "http://127.0.0.1:11434/"
prompts_dir = "prompts"

[models]
judge = "qwen3:4b"
embedders = ["nomic-embed-text", "bge-m3"]
writer = "gemma4, other"

[endpoints.openai]
base_url = "https://api.openai.com/v1/"
api_key_env = "OPENAI_API_KEY"

[prices]
"endpoint:openai/text-embedding-3-small" = 0.02
"other" = 1

[questions]
per_category = 12
categories = ["paraphrase", "keyword"]

[search]
k = 3
chunkers = ["recursive"]

[audit]
tiny_tokens = 10
near_duplicate_jaccard = 0.8

[budget]
usd = 1
minutes = 30
"""


def write(project: Path, text: str) -> Path:
    path = project / "ragcourt.toml"
    path.write_text(text)
    return path


def test_no_file_means_the_defaults(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    assert config.file is None
    assert config.stage_folder() == tmp_path / "ragcourt_stages"
    assert config.stages_dir is None
    assert config.role("judge").models == DEFAULT_MODELS["judge"]
    assert config.role("judge").source == "default"
    assert config.search.k == 5 and config.questions.per_category == 90


def test_every_section_is_read(tmp_path: Path) -> None:
    config = load_config(tmp_path, write(tmp_path, FULL))
    assert config.stages_dir == tmp_path / "my_stages"
    assert config.seed == 7 and config.ollama_url == "http://127.0.0.1:11434"
    assert config.prompts_dir == tmp_path / "prompts"
    assert config.role("judge").models == ("qwen3:4b",) and config.role("judge").source.endswith(
        "ragcourt.toml"
    )
    assert config.role("embedders").models == ("nomic-embed-text", "bge-m3")
    assert config.role("writer").models == ("gemma4", "other")
    assert config.role("doctor").source == "default"
    assert config.endpoints["openai"].base_url == "https://api.openai.com/v1"
    assert config.endpoints["openai"].api_key_env == "OPENAI_API_KEY"
    assert config.prices == {"endpoint:openai/text-embedding-3-small": 0.02, "other": 1.0}
    assert config.questions.per_category == 12 and config.questions.categories == ("paraphrase", "keyword")
    assert config.search.k == 3 and config.search.chunkers == ("recursive",)
    assert config.audit.tiny_tokens == 10 and config.audit.near_duplicate_jaccard == 0.8
    assert config.budget.usd == 1.0 and config.budget.minutes == 30.0


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ('stage_dir = "typo"\n', r"unknown setting stage_dir\. The settings are: stages_dir"),
        ("[models]\nranker = 'x'\n", r"\[models\]: unknown setting ranker"),
        ("[search]\nkk = 1\n", r"\[search\]: unknown setting kk"),
        ("[endpoints.x]\nurl = 'a'\n", r"\[endpoints.x\]: unknown setting url"),
        ("[endpoints]\nx = 1\n", "must be a table"),
        ("models = 1\n", "must be a table"),
        ("[search]\nk = 'five'\n", "k must be int"),
        ("[search]\nk = true\n", "k must be int"),
        ("[search]\nchunkers = []\n", "must be a list of names"),
        ("[models]\njudge = 3\n", "must be a list of names"),
        ("seed = 1.5\n", "seed must be int"),
        ('stages_dir = "   "\n', "stages_dir must be a non-empty string"),
        ("stages_dir = \n", "is not valid TOML"),
    ],
)
def test_mistakes_name_the_setting(tmp_path: Path, text: str, message: str) -> None:
    write(tmp_path, text)
    with pytest.raises(ConfigError, match=message):
        load_config(tmp_path)


def test_a_named_file_that_is_missing_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="does not exist"):
        load_config(tmp_path, tmp_path / "other.toml")


def test_a_byte_order_mark_is_accepted(tmp_path: Path) -> None:
    (tmp_path / "ragcourt.toml").write_bytes('﻿stages_dir = "s"\n'.encode())
    assert load_config(tmp_path).stages_dir == tmp_path / "s"


def test_a_file_that_is_not_utf8_says_so(tmp_path: Path) -> None:
    (tmp_path / "ragcourt.toml").write_bytes('stages_dir = "caf\xe9"\n'.encode("latin-1"))
    with pytest.raises(ConfigError, match="is not UTF-8"):
        load_config(tmp_path)


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads every file")
def test_a_file_that_cannot_be_read_says_so(tmp_path: Path) -> None:
    config = write(tmp_path, 'stages_dir = "s"\n')
    config.chmod(0)
    try:
        with pytest.raises(ConfigError, match="cannot be read"):
            load_config(tmp_path)
    finally:
        config.chmod(0o600)
