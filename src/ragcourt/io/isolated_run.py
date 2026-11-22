"""Running a model-written chunker in a separate Python process (design §12, D-017).

``python -I`` (no user site, no environment variables read by Python), a fresh temporary working folder,
an environment without keys or proxies, one document on stdin and JSON on stdout, a timeout and an output
size limit. This isolates ragcourt from hangs and crashes; it is not a security sandbox: the user's approval
of the exact code is the safety step, and ragcourt says so.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from ragcourt.errors import GeneratedCodeRejected

RUNNER = (
    "import json, runpy, sys; space = runpy.run_path(sys.argv[1]); "
    "print(json.dumps(space['chunk'](sys.stdin.read())))"
)
MAX_OUTPUT_FACTOR = 4  # the output may be at most this many times the input, plus a little


def run_chunker(code_file: Path, text: str, timeout: float) -> object:
    """The chunker's output for one text, or ``GeneratedCodeRejected`` saying why it has none."""
    with tempfile.TemporaryDirectory() as folder:
        try:
            finished = subprocess.run(  # noqa: S603 (the interpreter itself, on code the user approved)
                [sys.executable, "-I", "-c", RUNNER, str(code_file.resolve())],
                input=text,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=folder,
                env={"PATH": os.defpath},
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise GeneratedCodeRejected(
                f"It ran longer than {timeout:g} s on one document and was stopped."
            ) from error
    if finished.returncode != 0:
        last = (finished.stderr.strip().splitlines() or ["no message"])[-1]
        raise GeneratedCodeRejected(f"It failed: {last}")
    if len(finished.stdout) > MAX_OUTPUT_FACTOR * len(text) + 10_000:
        raise GeneratedCodeRejected("Its output is far larger than its input.")
    try:
        return json.loads(finished.stdout)
    except json.JSONDecodeError as error:
        raise GeneratedCodeRejected("It did not print JSON.") from error
