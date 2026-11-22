"""Stage specs: a stage's name with its parameters, as written on the command line (design §7.1).

``recursive:size=512,overlap=64`` is the stage ``recursive`` called with ``size=512, overlap=64``.
Values are read as integers, then numbers, then ``true``/``false``, else kept as text. Parameters are
checked against the stage function's own keyword arguments, so a typo is an error, not a silent default.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass

from ragcourt.errors import ConfigError

Value = int | float | bool | str


@dataclass(frozen=True)
class StageSpec:
    """A stage name and its parameters, in the order written."""

    name: str
    params: tuple[tuple[str, Value], ...] = ()

    def kwargs(self) -> dict[str, Value]:
        """The parameters as keyword arguments."""
        return dict(self.params)

    def __str__(self) -> str:
        if not self.params:
            return self.name
        return self.name + ":" + ",".join(f"{key}={_text(value)}" for key, value in self.params)


def _text(value: Value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _value(raw: str) -> Value:
    for convert in (int, float):
        try:
            return convert(raw)
        except ValueError:
            pass
    if raw in ("true", "false"):
        return raw == "true"
    return raw


def parse_spec(text: str) -> StageSpec:
    """Read ``name`` or ``name:key=value,…``; a malformed spec is an error that shows the form."""
    name, _, rest = text.strip().partition(":")
    params: list[tuple[str, Value]] = []
    for item in filter(None, rest.split(",")):
        key, equals, raw = item.partition("=")
        if not equals or not key.strip():
            raise ConfigError(f"{text!r} is not a stage spec: write name:key=value,key=value.")
        params.append((key.strip(), _value(raw.strip())))
    if not name:
        raise ConfigError(f"{text!r} has no stage name: write name or name:key=value.")
    return StageSpec(name.strip(), tuple(params))


def check_params(function: object, spec: StageSpec, *, injected: tuple[str, ...] = ()) -> None:
    """Refuse parameters the stage function does not take (``injected`` ones are given by ragcourt)."""
    accepted = _keyword_parameters(function)
    for key, _ in spec.params:
        if key in injected or key not in accepted:
            known = ", ".join(sorted(set(accepted) - set(injected))) or "none"
            raise ConfigError(f"The stage {spec.name!r} has no parameter {key!r}; its parameters: {known}.")


def _keyword_parameters(function: object) -> list[str]:
    if not callable(function):
        return []
    signature = inspect.signature(function)
    kinds = (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
    with_default = [p for p in signature.parameters.values() if p.default is not inspect.Parameter.empty]
    return [p.name for p in with_default if p.kind in kinds]
