"""How much memory this machine has: RAM from the OS, GPU memory from ``nvidia-smi`` when present (§11.3).

Ollama has no route that reports a GPU's total memory, so ``nvidia-smi`` is asked; without it the GPU memory
is unknown and said so.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys


def ram_gb() -> float:
    """Physical memory in GB (0 when the OS does not say)."""
    if sys.platform == "win32":  # no sysconf there
        return 0.0
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1e9
    except (ValueError, OSError, AttributeError):
        return 0.0


def gpu_gb() -> float | None:
    """The largest NVIDIA GPU's memory in GB, or None when there is none or it cannot be read."""
    tool = shutil.which("nvidia-smi")
    if tool is None:
        return None
    try:
        output = subprocess.run(  # noqa: S603 (a fixed local tool, found on PATH, no user input)
            [tool, "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    sizes = [float(line) for line in output.split() if line.strip().replace(".", "", 1).isdigit()]
    return max(sizes) / 1024 if sizes else None
