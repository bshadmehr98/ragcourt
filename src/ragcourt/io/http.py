"""JSON over HTTP with the standard library: the only code in ragcourt that opens a connection (§11.1).

Timeouts, 429 and 5xx are retried three times with a growing wait; anything else stops at once with an
``EndpointError`` that names the address, the status and what to check. Keys travel only in headers and
never appear in messages.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any, cast

from ragcourt.errors import EndpointError

RETRY_WAITS = (1.0, 2.0, 4.0)
Sleep = Callable[[float], None]


def request_json(
    url: str,
    body: dict[str, Any] | None = None,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 300.0,
    sleep: Sleep = time.sleep,
) -> dict[str, Any]:
    """POST ``body`` as JSON (or GET when it is None) and return the JSON reply, retrying what may pass."""
    for wait in (*RETRY_WAITS, None):
        try:
            return _once(url, body, headers or {}, timeout)
        except EndpointError as error:
            if not error.retryable or wait is None:
                raise
            sleep(wait)
    raise AssertionError("unreachable")  # pragma: no cover


def _once(url: str, body: dict[str, Any] | None, headers: dict[str, str], timeout: float) -> dict[str, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    _check_scheme(url)
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **headers})  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return _parse(url, response.read())
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:300]
        retryable = error.code == 429 or error.code >= 500
        raise EndpointError(f"{url} answered {error.code}: {detail}", retryable=retryable) from error
    except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
        reason = getattr(error, "reason", error)
        timed_out = isinstance(error, TimeoutError) or isinstance(reason, TimeoutError)
        message = f"{url} could not be reached: {reason}. Is the server running, and is the address right?"
        raise EndpointError(message, retryable=timed_out) from error


def _check_scheme(url: str) -> None:
    """Only http and https: the S310 noqa above rests on this check."""
    if not url.startswith(("http://", "https://")):
        raise EndpointError(f"{url} is not an http(s) address; check the configuration.", retryable=False)


def _parse(url: str, raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise EndpointError(f"{url} did not answer JSON: {raw[:200]!r}", retryable=False) from error
    if not isinstance(value, dict):
        raise EndpointError(f"{url} answered {type(value).__name__}, not a JSON object.", retryable=False)
    return cast(dict[str, Any], value)


def stream_json_lines(url: str, body: dict[str, Any], *, timeout: float = 3600.0) -> list[dict[str, Any]]:
    """POST ``body`` and read a reply of one JSON object per line (Ollama's pull progress)."""
    data = json.dumps(body).encode("utf-8")
    _check_scheme(url)
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            raw_lines = list(response)
    except urllib.error.URLError as error:
        raise EndpointError(f"{url} could not be reached: {error.reason}.", retryable=False) from error
    return [_parse(url, raw) for raw in raw_lines if raw.strip()]
