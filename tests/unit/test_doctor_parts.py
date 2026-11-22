"""Doctor's parts: sampling, advice, code, validation and the isolated run (design §12)."""

from pathlib import Path

import pytest

from ragcourt import Document, GeneratedCodeRejected
from ragcourt.core.doctor import (
    chunker_menu,
    code_hash,
    read_advice,
    read_code,
    sample,
    samples_text,
    validate,
)
from ragcourt.io.isolated_run import run_chunker


def test_sampling_is_bounded_cut_and_seeded() -> None:
    documents = [Document(f"{n}.md", "x" * 5000) for n in range(12)]
    first = sample(documents, 1)
    assert len(first) == 8 and all(len(d.text) == 4000 for d in first)
    assert first == sample(documents, 1) and first != sample(documents, 2)
    assert "--- 0.md ---" in samples_text(sample(documents[:2], 0))
    assert "recursive: size=512, overlap=64" in chunker_menu()


def test_advice_keeps_known_chunkers_and_drops_the_rest() -> None:
    reply = '{"structure": {"headings": "many"}, "recommendations": [{"chunker": "markdown:size=300", "why": "headings"}, {"chunker": "magic"}, {"chunker": "recursive:sise=1"}, "sentence"]}'
    advice = read_advice(reply)
    assert advice.structure == {"headings": "many"}
    assert advice.recommended == [("markdown:size=300", "headings"), ("sentence", "")]
    assert [spec for spec, _ in advice.dropped] == ["magic", "recursive:sise=1"]
    assert read_advice("not json").recommended == []


def test_code_is_found_in_a_fence_or_bare() -> None:
    assert (
        read_code("Here:\n```python\ndef chunk(text):\n    return [text]\n```")
        == "def chunk(text):\n    return [text]\n"
    )
    assert read_code("def chunk(text):\n    return []") is not None
    assert read_code("print('no function')") is None
    assert len(code_hash("x")) == 64


def test_validation_names_the_first_failure() -> None:
    document = Document("d.md", "one two three")
    assert validate(document, ["one", "two three"]) == ["one", "two three"]
    for output, message in [
        ("text", "not a list"),
        (["one", ""], "item 1"),
        (["four"], "not text of the document"),
    ]:
        with pytest.raises(GeneratedCodeRejected, match=message):
            validate(document, output)


@pytest.mark.parametrize(
    ("code", "message"),
    [
        ("import time\ndef chunk(text):\n    time.sleep(10)\n", "longer than"),
        ("def chunk(text):\n    raise ValueError('boom')\n", "ValueError: boom"),
        ("def chunk(text):\n    return [text] * 100\n", "far larger"),
        ("import sys\ndef chunk(text):\n    sys.stdout.write('x')\n    sys.exit(0)\n", "did not print JSON"),
    ],
)
def test_the_isolated_run_stops_bad_code(tmp_path: Path, code: str, message: str) -> None:
    path = tmp_path / "chunk.py"
    path.write_text(code)
    with pytest.raises(GeneratedCodeRejected, match=message):
        run_chunker(path, "some text " * 10, timeout=1.0)


def test_the_isolated_run_gets_no_keys(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    path = tmp_path / "chunk.py"
    path.write_text("import os\ndef chunk(text):\n    return [str(sorted(os.environ))]\n")
    assert "OPENAI_API_KEY" not in str(run_chunker(path, "x", timeout=5.0))
