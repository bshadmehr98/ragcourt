"""The bundled corpus holds the cases the audit, the questions and blame will need (design §15.2)."""

import re
from collections import Counter

import pytest

from ragcourt import Document, load_documents
from ragcourt.testing import corpus_path, fake_tokens

HEADER = "Larkspur Docs · version 3.2"


@pytest.fixture(scope="module")
def documents() -> dict[str, Document]:
    corpus = load_documents(corpus_path())
    assert corpus.skipped == ()
    return {document.id: document for document in corpus.documents}


def word_shingles(text: str, size: int = 5) -> set[tuple[str, ...]]:
    words = re.findall(r"\w+", text.lower())
    return {tuple(words[i : i + size]) for i in range(len(words) - size + 1)}


def paragraph_under(text: str, heading: str) -> str:
    return text.split(heading, 1)[1].strip().split("\n\n")[0]


def test_a_dozen_documents_in_every_format(documents: dict[str, Document]) -> None:
    assert len(documents) == 13
    suffixes = Counter(name.rsplit(".", 1)[1] for name in documents)
    assert set(suffixes) == {"md", "txt", "rst", "html"}


def test_a_running_header_repeats_across_a_third_of_the_documents(documents: dict[str, Document]) -> None:
    with_header = [doc for doc in documents.values() if doc.text.startswith(HEADER)]
    assert len(with_header) >= 0.3 * len(documents)
    assert len(with_header) < len(documents)


def test_tables_in_markdown_and_html(documents: dict[str, Document]) -> None:
    assert "| max_inflight | LARKSPUR_MAX_INFLIGHT | 200 |" in documents["configuration.md"].text
    assert "| larkspur_jobs_waiting | gauge | jobs waiting, per queue |" in documents["monitoring.html"].text


def test_fenced_and_indented_code(documents: dict[str, Document]) -> None:
    assert "```bash\npip install larkspur==3.2.1\n" in documents["install.md"].text
    assert '\n    @larkspur.periodic("0 7 * * 1-5", queue="reports")\n' in documents["scheduling.md"].text
    assert "```\n- alert: LarkspurBacklog\n" in documents["monitoring.html"].text


def test_a_section_longer_than_the_fake_embedders_limit(documents: dict[str, Document]) -> None:
    section = documents["queues.md"].text.split("## How a job moves through a queue")[1].split("\n## ")[0]
    assert len(fake_tokens(section)) > 512


def test_a_near_duplicate_paragraph_in_two_documents(documents: dict[str, Document]) -> None:
    first = paragraph_under(documents["install.md"].text, "## Check that it works")
    second = paragraph_under(documents["upgrading.md"].text, "## After the upgrade")
    a, b = word_shingles(first), word_shingles(second)
    assert first != second
    assert len(a & b) / len(a | b) >= 0.9


def test_headings_in_markdown_html_and_setext_style(documents: dict[str, Document]) -> None:
    assert "\n## Who it is for\n" in documents["index.md"].text
    assert "## What to alert on" in documents["monitoring.html"].text
    assert "Heartbeat\n---------\n" in documents["glossary.rst"].text


def test_sentences_that_end_in_abbreviations(documents: dict[str, Document]) -> None:
    assert "e.g. a report" in documents["scheduling.md"].text
    assert "approx. every ten" in documents["scheduling.md"].text


def test_twin_passages_share_their_words(documents: dict[str, Document]) -> None:
    retries = set(re.findall(r"[a-z]{4,}", documents["retries.md"].text.lower()))
    timeouts = set(re.findall(r"[a-z]{4,}", documents["timeouts.md"].text.lower()))
    assert len(retries & timeouts) / len(retries | timeouts) > 0.3


@pytest.mark.parametrize(
    ("term", "home"),
    [
        ("LARKSPUR_MAX_INFLIGHT", "configuration.md"),
        ("lark-sweeper", "scheduling.md"),
        ("--drain-timeout", "timeouts.md"),
    ],
)
def test_rare_terms_live_in_one_document(documents: dict[str, Document], term: str, home: str) -> None:
    assert [name for name, doc in documents.items() if term in doc.text] == [home]


def test_negations_and_numbers_in_prose(documents: dict[str, Document]) -> None:
    assert "are never logged" in documents["security.md"].text
    assert "not supported: the worker" in documents["install.md"].text
    assert "The first retry waits 10 seconds" in documents["retries.md"].text
