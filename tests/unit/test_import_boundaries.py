"""The core imports nothing optional (CONTRIBUTING.md, "Code conventions")."""

import subprocess
import sys

# Libraries that only optional extras may bring in; importing ragcourt must not load any of them.
OPTIONAL = (
    "tiktoken",
    "tokenizers",
    "pypdf",
    "sentence_transformers",
    "torch",
    "chonkie",
    "langchain",
    "numpy",
)


def test_core_import_pulls_no_extras() -> None:
    code = f"import sys, ragcourt\nprint([m for m in sys.modules if m.startswith({OPTIONAL!r})])\n"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "[]"
