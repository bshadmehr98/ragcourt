"""Running a model-written chunker in a separate Python process (design §12, D-017).

``python -I`` (no user site, no environment variables read by Python), a fresh temporary working folder,
an environment without keys or proxies, one document on stdin and JSON on stdout, a timeout and an output
size limit. This isolates ragcourt from hangs and crashes; it is not a security sandbox: the user's approval
of the exact code is the safety step, and ragcourt says so.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import IO

from ragcourt.errors import GeneratedCodeRejected

# Before the code runs, files it writes (stdout and stderr included) are capped where the OS allows it.
RUNNER = (
    "import json, runpy, sys\n"
    "try:\n import resource; resource.setrlimit(resource.RLIMIT_FSIZE, (int(sys.argv[2]),) * 2)\n"
    "except (ImportError, ValueError, OSError): pass\n"
    "space = runpy.run_path(sys.argv[1]); print(json.dumps(space['chunk'](sys.stdin.read())))"
)
MAX_OUTPUT_FACTOR = 4  # the output may be at most this many times the input, plus a little


def run_chunker(code_file: Path, text: str, timeout: float) -> object:
    """The chunker's output for one text, or ``GeneratedCodeRejected`` saying why it has none."""
    limit = MAX_OUTPUT_FACTOR * len(text.encode("utf-8")) + 10_000
    with tempfile.TemporaryDirectory() as folder:
        out, err = Path(folder) / "out", Path(folder) / "err"
        with out.open("wb") as stdout, err.open("wb") as stderr:
            code = _run([str(code_file.resolve()), str(limit)], text, (stdout, stderr), folder, timeout)
        if out.stat().st_size >= limit:  # at the cap: the OS stopped it there
            raise GeneratedCodeRejected("Its output is far larger than its input.")
        printed, message = (
            out.read_text("utf-8", "replace"),
            err.read_bytes()[-2000:].decode("utf-8", "replace"),
        )
    if code != 0:
        last = (message.strip().splitlines() or ["no message"])[-1]
        raise GeneratedCodeRejected(f"It failed: {last}")
    try:
        return json.loads(printed)
    except json.JSONDecodeError as error:
        raise GeneratedCodeRejected("It did not print JSON.") from error


def _run(
    args: list[str], text: str, streams: tuple[IO[bytes], IO[bytes]], folder: str, timeout: float
) -> int:
    """Start the runner in its own process group, so a timeout stops everything it started."""
    process = subprocess.Popen(  # noqa: S603 (the interpreter itself, on code the user approved)
        [sys.executable, "-I", "-c", RUNNER, *args],
        stdin=subprocess.PIPE,
        stdout=streams[0],
        stderr=streams[1],
        cwd=folder,
        env={"PATH": os.defpath},
        start_new_session=os.name == "posix",
    )
    try:
        process.communicate(text.encode("utf-8"), timeout=timeout)
    except subprocess.TimeoutExpired as error:
        _stop(process)
        raise GeneratedCodeRejected(
            f"It ran longer than {timeout:g} s on one document and was stopped."
        ) from error
    except BaseException:  # Ctrl-C: its own process group does not get the terminal's signal
        _stop(process)
        raise
    return process.returncode


def _stop(process: subprocess.Popen[bytes]) -> None:
    if os.name == "posix":
        os.killpg(process.pid, signal.SIGKILL)
    else:  # pragma: no cover (Windows)
        process.kill()
    process.wait()
