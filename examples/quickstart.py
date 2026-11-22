"""Quickstart: audit a folder of documents, with no model and no network.

What: how four chunkers cut the bundled documents: cut sentences, lost headings, split tables, sizes.
How: ``ragcourt audit`` on the bundled corpus; sizes are estimated because no embedder answers here.
Why: the audit is the seconds-long first look; with Ollama running, sizes are the embedder's own tokens.
Run: ``python examples/quickstart.py`` (from any folder; nothing is written but ``.ragcourt/``).
"""

import socket
import tempfile
from pathlib import Path

from ragcourt.cli import main
from ragcourt.testing import corpus_path


def refuse(self: socket.socket, address: object) -> None:  # noqa: ARG001 (socket.connect's signature)
    """No connection: this example runs offline."""
    raise ConnectionRefusedError("this example runs offline")


socket.socket.connect = refuse  # type: ignore[method-assign]  # no Ollama here: sizes are estimated
with tempfile.TemporaryDirectory() as folder:
    code = main(["audit", str(corpus_path()), "--workdir", str(Path(folder) / ".ragcourt"), "-q"])
assert code == 0
