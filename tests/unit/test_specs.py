"""Stage specs (design §7.1)."""

import pytest

from ragcourt import ConfigError
from ragcourt.stages.specs import StageSpec, check_params, parse_spec


def test_names_and_typed_parameters() -> None:
    spec = parse_spec("recursive:size=512,overlap=6.5,strict=true,mode=fast,off=false")
    assert spec == StageSpec(
        "recursive", (("size", 512), ("overlap", 6.5), ("strict", True), ("mode", "fast"), ("off", False))
    )
    assert str(spec) == "recursive:size=512,overlap=6.5,strict=true,mode=fast,off=false"
    assert parse_spec(" markdown ") == StageSpec("markdown")
    assert str(parse_spec("markdown")) == "markdown"
    assert parse_spec("a:x=1").kwargs() == {"x": 1}


@pytest.mark.parametrize("text", ["a:size", "a:=1", ":size=1", ""])
def test_malformed_specs_say_the_form(text: str) -> None:
    with pytest.raises(ConfigError, match="stage"):
        parse_spec(text)


def test_unknown_parameters_list_the_known_ones() -> None:
    def chunk(text: str, size: int = 1, overlap: int = 0) -> list[str]:
        return [text]

    check_params(chunk, parse_spec("c:size=2"))
    with pytest.raises(ConfigError, match="has no parameter 'sise'; its parameters: overlap, size"):
        check_params(chunk, parse_spec("c:sise=2"))
    with pytest.raises(ConfigError, match="no parameter 'client'"):
        check_params(lambda client=None: client, parse_spec("e:client=x"), injected=("client",))
    with pytest.raises(ConfigError, match="its parameters: none"):
        check_params(42, parse_spec("x:a=1"))
