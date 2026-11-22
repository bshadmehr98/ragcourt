"""The parts of question writing: windows, categories, rules, replies, splits (design §6)."""

import pytest

from ragcourt import Document
from ragcourt.core.categories import CATEGORIES
from ragcourt.core.question_rules import duplicate_of, rule_problem
from ragcourt.core.split import assign_splits, question_id
from ragcourt.core.verdicts import fill, is_unknown, json_object, read_draft, read_verdict
from ragcourt.core.windows import index_corpus, windows_of
from ragcourt.types.questions import Offer, Question

PARAGRAPH = "Word " * 50 + "end.\n\n"


def question(
    text: str = "What is it?",
    start: int = 0,
    end: int = 10,
    document: str = "a.md",
    category: str = "paraphrase",
) -> Question:
    return Question(
        question_id(document, start, end, text), text, category, document, start, end, "q" * (end - start)
    )


def test_windows_follow_paragraphs_and_skip_tiny_ones() -> None:
    document = Document("a.md", PARAGRAPH * 10 + "tiny\n")
    windows = windows_of(document, 600)
    assert all(document.text[w.start : w.end].endswith(("end.", "tiny")) for w in windows)
    assert all(w.end - w.start >= 200 for w in windows) and len(windows) == 5
    assert windows_of(Document("b.md", "short\n\nalso short"), 600) == []


def test_reading_replies() -> None:
    assert json_object('<think>x</think> sure: {"a": 1} done') == {"a": 1}
    assert json_object("no json") is None and json_object("[1]") is None and json_object("{bad}") is None
    assert read_draft('{"question": " Q ", "quote": " A "}').question == "Q"  # type: ignore[union-attr]
    assert read_draft('{"question": "Q"}') is None and read_draft("nothing") is None
    assert read_verdict('{"verdict": "Correct", "reason": "r"}').passed is True
    assert read_verdict('{"verdict": "no"}').reason == "no reason given"
    assert read_verdict('{"verdict": "maybe"}').passed is None
    assert read_verdict("garbage").passed is None
    assert is_unknown("UNKNOWN.") and is_unknown("<think>hm</think>unknown") and not is_unknown("It is 5.")
    assert fill("{{a}} and {{b}} and {{a}}", a="x", b="y") == "x and y and x"


@pytest.mark.parametrize(
    ("asked", "quote", "category", "problem"),
    [
        ("What is it?", "Too short a quote.", "paraphrase", "at least 6"),
        ("What is it?", "x = 1; y = [2]; z = {3}; f(a) | b", "paraphrase", "not a sentence"),
        ("What is it?", "word " * 130, "paraphrase", "longer than 120"),
        ("Why?", "This quote is long enough to pass the rules.", "paraphrase", "fewer than 3"),
        ("two words", "This quote is long enough to pass the rules.", "keyword", None),
    ],
)
def test_code_rules(asked: str, quote: str, category: str, problem: str | None) -> None:
    found = rule_problem(asked, quote, category)
    assert (found is None) if problem is None else (problem in (found or ""))


def test_duplicates_by_quote_overlap_or_question_text() -> None:
    earlier = question("How long are jobs kept after finishing?", 0, 100)
    assert duplicate_of(question("Something else entirely here?", 40, 120), [earlier]) is earlier
    assert duplicate_of(question("How long are jobs kept after finishing", 500, 600), [earlier]) is earlier
    assert duplicate_of(question("Different words about cron?", 500, 600), [earlier]) is None
    assert (
        duplicate_of(question("Something else entirely here?", 40, 120, document="b.md"), [earlier]) is None
    )


def test_splits_are_a_third_dev_per_category_and_stable() -> None:
    questions = [
        question(f"Q{n}?", n * 10, n * 10 + 5, category="keyword" if n % 2 else "numeric") for n in range(30)
    ]
    split = assign_splits(questions, seed=1)
    for category in ("keyword", "numeric"):
        members = [q for q in split if q.category == category]
        assert sum(q.split == "dev" for q in members) == len(members) // 3
    assert assign_splits(questions, seed=1) == split
    assert assign_splits(questions, seed=2) != split


def two_windows():  # type: ignore[no-untyped-def]
    documents = [
        Document("a.md", "The worker never retries an aborted job. " * 8),
        Document("b.md", "The worker retries a failed job later. " * 8),
    ]
    index = index_corpus(documents, 2000)
    return index, Offer(index.windows[0], term="failed, later", twin=index.windows[1])


@pytest.mark.parametrize(
    ("category", "asked", "quote", "passes"),
    [
        (
            "paraphrase",
            "Which statement covers the alpha matter?",
            "The worker never retries an aborted job.",
            True,
        ),
        (
            "paraphrase",
            "Does the worker retry an aborted job?",
            "The worker never retries an aborted job.",
            False,
        ),
        ("keyword", "worker retries", "", True),
        ("keyword", "does the worker retry?", "", False),
        ("exact_term", "What does failed, later mean?", "failed, later is the term.", True),
        ("exact_term", "What is the limit?", "max_inflight is 200.", False),
        ("negation", "What is never retried?", "Jobs are never retried.", True),
        ("negation", "What is retried?", "Jobs are retried.", False),
        ("numeric", "How many?", "It is 5.", True),
        ("numeric", "How many?", "It is five.", True),
        ("numeric", "How many?", "It is several.", False),
        ("distractor", "How does the worker job get failed later?", "", True),
        ("distractor", "What about an aborted job?", "", False),
    ],
)
def test_category_checks(category: str, asked: str, quote: str, passes: bool) -> None:
    index, offer = two_windows()
    assert (CATEGORIES[category].check(asked, quote, offer, index) is None) is passes


def test_a_distractor_needs_its_twin() -> None:
    index, offer = two_windows()
    assert CATEGORIES["distractor"].check("x", "", Offer(offer.window), index) == "no twin passage"


def test_offers_per_category() -> None:
    texts = [
        Document("a.md", "Set LARKSPUR_MAX_INFLIGHT to 200. It is never zero. " * 6),
        Document("b.md", "Other words about cron and the sweeper run. " * 6),
    ]
    index = index_corpus(texts, 2000)
    assert [offer.term for offer in CATEGORIES["exact_term"].offers(index)] == ["LARKSPUR_MAX_INFLIGHT"]
    assert len(CATEGORIES["negation"].offers(index)) == 1 and len(CATEGORIES["numeric"].offers(index)) == 1
    assert len(CATEGORIES["keyword"].offers(index)) == 2
    assert index.documents_with("cron") == 1 and index.documents_with("cron") == 1  # remembered


def test_a_sentence_with_markdown_links_is_prose_and_a_line_of_code_is_not() -> None:
    linked = (
        "Deploy your app to **[FastAPI Cloud](https://fastapicloud.com)** with one command: `fastapi deploy`."
    )
    assert rule_problem("How is the app put online?", linked, "paraphrase") is None
    code = "CurrentUser = Annotated[User, Depends(get_current_user)] if x else (y)"
    assert (
        rule_problem("How is a user found?", code, "paraphrase")
        == "the quote is not a sentence (a name or a line of code)"
    )


def test_offers_take_one_passage_from_each_document_in_turn() -> None:
    from ragcourt.core.generate import ordered_offers

    def text(name: str, count: int) -> str:
        return "".join(
            f"In {name} part {n} explains a different matter at some length.\n\n" for n in range(count)
        )

    long = Document("long.md", text("long", 600))
    short = [Document(f"s{n}.md", text(f"s{n}", 40)) for n in range(3)]
    order = [
        offer.window.document for offer in ordered_offers(index_corpus([long, *short], 2000), "paraphrase", 0)
    ]
    assert set(order[:4]) == {"long.md", "s0.md", "s1.md", "s2.md"}  # every document before any second
