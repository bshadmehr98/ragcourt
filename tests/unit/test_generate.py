"""The question loop with scripted models: resume, unreadable replies, limits (design §6.2, §10.4)."""

from ragcourt.core.generate import Journal, Wanted, generate
from ragcourt.core.question_checks import Models
from ragcourt.core.windows import index_corpus
from ragcourt.io.documents import load_documents
from ragcourt.io.prompts import load_prompts
from ragcourt.testing import ScriptedReplies, corpus_path
from ragcourt.types.questions import Dropped, Question

INDEX = index_corpus(load_documents(corpus_path()).documents, 2000)
PROMPTS = {name: prompt.text for name, prompt in load_prompts().items()}


def run(replies, done=(), per_category=2, categories=("keyword", "numeric")):  # type: ignore[no-untyped-def]
    recorded: list[object] = []
    reports: list[object] = []
    models = Models(replies, replies, replies, "scripted")
    wanted = Wanted(per_category, categories, 6, 0)
    outcomes = generate(INDEX, PROMPTS, models, wanted, Journal(list(done), recorded.append, reports.append))
    return outcomes, recorded, reports


def test_a_run_resumed_halfway_gives_the_same_questions() -> None:
    full, _, _ = run(ScriptedReplies())
    half = full[:2]
    resumed, recorded, _ = run(ScriptedReplies(), done=half)
    assert resumed == full and recorded == full[2:]


def test_unreadable_judge_replies_are_asked_twice_then_kept() -> None:
    def replies(prompt: str) -> str:
        if prompt.startswith(("You check", "You grade")):
            return "I refuse to answer in JSON"
        return ScriptedReplies()(prompt)

    outcomes, _, _ = run(replies, categories=("keyword",))
    kept = [item for item in outcomes if isinstance(item, Question)]
    assert kept and "unreadable twice" in kept[0].verdicts[1].reason


def test_a_writer_without_json_is_dropped_with_its_reason() -> None:
    outcomes, _, reports = run(lambda prompt: "no json here", categories=("keyword",))
    assert all(
        isinstance(item, Dropped) and item.reason == "reply without a question and a quote"
        for item in outcomes
    )
    assert reports[-1].finished  # type: ignore[attr-defined]


def test_the_request_limit_stops_a_category() -> None:
    def replies(prompt: str) -> str:
        return ScriptedReplies(unverbatim=True)(prompt)

    models = Models(replies, replies, replies, "scripted")
    outcomes = generate(
        INDEX,
        PROMPTS,
        models,
        Wanted(1, ("keyword",), 2, 0),
        Journal([], lambda item: None, lambda progress: None),
    )
    assert len(outcomes) == 2
