"""Each audit check fires on its case and not on its near miss (design §5.1, guarantee 2)."""

from ragcourt import Document
from ragcourt.core.audit import CHECKS, CODES, audit
from ragcourt.core.offsets import chunk_spans
from ragcourt.core.structure import structure_of
from ragcourt.text_units import count_tokens
from ragcourt.types.audit import AuditContext, AuditSettings


def findings(
    texts: dict[str, list[str]], *, limit: int | None = None, settings: AuditSettings | None = None
) -> list[tuple[str, str, int]]:
    """(code, document, chunk index) of every finding, given each document's chunk texts."""
    documents = {name: Document(name, "".join(pieces)) for name, pieces in texts.items()}
    chunks = []
    for name, pieces in texts.items():
        for chunk in chunk_spans(documents[name], pieces, "test"):
            chunks.append(chunk.__class__(chunk.document, len(chunks), chunk.start, chunk.end, chunk.text))
    context = AuditContext(
        documents,
        {name: structure_of(document.text) for name, document in documents.items()},
        [count_tokens(chunk.text) for chunk in chunks],
        True,
        limit,
        settings or AuditSettings(),
    )
    return [(f.code, f.chunk.document, f.chunk.index) for f in audit(chunks, context)]


def codes(found: list[tuple[str, str, int]]) -> list[str]:
    return [code for code, _, _ in found]


def test_the_checks_are_listed_in_order() -> None:
    assert [check.CODE for check in CHECKS] == CODES
    assert len(CODES) == 8


def test_cut_mid_sentence() -> None:
    cut = findings({"a.md": ["The job runs and the ", "worker stops it."]})
    assert ("cut.mid_sentence", "a.md", 0) in cut
    near = findings({"a.md": ["The job runs, e.g. ", "a report."], "b.md": ["Ends with etc.", " Next."]})
    assert "cut.mid_sentence" not in codes(near[:1])
    block_end = findings({"a.md": ["A list item without a stop", "\n\nNew paragraph."]})
    assert "cut.mid_sentence" not in codes(block_end)
    in_code = findings({"a.md": ["Code:\n\n```\nx = 1\n", "y = 2\n```\n"]})
    assert "cut.mid_sentence" not in codes(in_code)


def test_context_no_heading() -> None:
    lost = findings({"a.md": ["# Retries\n\nFirst part. ", "Second part."]})
    assert ("context.no_heading", "a.md", 1) in lost
    kept = findings({"a.md": ["# Retries\n\nFirst. ", "Retries again: second."]})
    assert ("context.no_heading", "a.md", 1) not in kept
    before_any = findings({"a.md": ["Intro. ", "More intro."]})
    assert "context.no_heading" not in codes(before_any)


def test_split_table() -> None:
    table = "| a | b |\n| - | - |\n| 1 | 2 |\n"
    split = findings({"a.md": ["Text.\n\n| a | b |\n", "| - | - |\n| 1 | 2 |\n"]})
    assert "split.table" in codes(split)
    whole = findings({"a.md": ["Text.\n\n", table]})
    assert "split.table" not in codes(whole)


def test_split_code() -> None:
    split = findings({"a.md": ["```\nline 1\n", "line 2\n```\n"]})
    assert "split.code" in codes(split)
    whole = findings({"a.md": ["Text.\n\n", "```\nline 1\nline 2\n```\n"]})
    assert "split.code" not in codes(whole)


def test_boilerplate_repeated() -> None:
    header = "Acme Docs v1\n"
    docs = {f"{n}.md": [header, f"Body {n} is unique text.\n"] for n in range(4)}
    found = findings(docs)
    assert sum(1 for code in codes(found) if code == "boilerplate.repeated") == 4
    single = findings({"a.md": [header, "Body."]})
    assert "boilerplate.repeated" not in codes(single)


def test_duplicate_near() -> None:
    sentence = " ".join(f"word{n}" for n in range(60)) + " "
    found = findings({"a.md": [sentence + "one. "], "b.md": [sentence + "two. "]})
    assert ("duplicate.near", "b.md", 1) in found
    different = findings(
        {
            "a.md": [sentence + "x. "],
            "b.md": ["a completely different text about cron schedules and the sweeper. "],
        }
    )
    assert "duplicate.near" not in codes(different)
    short = findings({"a.md": ["a b c. "], "b.md": ["a b c. "]})
    assert "duplicate.near" not in codes(short)


def test_sizes() -> None:
    long_text = "word " * 30 + "end."
    found = findings({"a.md": ["Tiny one. ", long_text]}, limit=20)
    assert ("size.tiny", "a.md", 0) in found
    assert ("size.over_limit", "a.md", 1) in found
    assert ("size.over_limit", "a.md", 0) not in found
    unknown_limit = findings({"a.md": [long_text]}, limit=None)
    assert "size.over_limit" not in codes(unknown_limit)


def test_an_exact_copy_is_found_even_behind_a_footer_in_every_chunk() -> None:
    footer = " ".join(f"footer{n}" for n in range(26)) + ". "
    pieces = [" ".join(f"t{chunk}w{n}" for n in range(30)) + ". " + footer for chunk in range(80)]
    pieces.append(pieces[70])  # the 81st chunk repeats the 71st exactly
    found = findings({"a.md": pieces})
    assert ("duplicate.near", "a.md", 80) in found
