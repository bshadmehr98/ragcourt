"""The checks a located question goes through: code rules, category, duplicates, judges (design §6.2).

In order: the code rules (D-028), the category's own check, duplicates, the judge's category check where
§6.7 asks for one, validity, and whether the writer can answer it without the documents. Every check leaves
a verdict with its reason, kept or dropped.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from ragcourt.core.categories import CATEGORIES
from ragcourt.core.question_rules import duplicate_of, rule_problem
from ragcourt.core.verdicts import JudgeReply, fill, is_unknown, read_verdict
from ragcourt.core.windows import CorpusIndex
from ragcourt.types.questions import Dropped, Offer, Question, Verdict

Chat = Callable[[str], str]
Outcome = Question | Dropped


@dataclass(frozen=True)
class Models:
    """The writer and the judge as callables, with the judge's name for the verdicts."""

    write: Chat
    answer: Chat
    judge: Chat
    judge_name: str


Context = tuple[CorpusIndex, dict[str, str], Models]


def check_question(question: Question, offer: Offer, context: Context, kept: list[Question]) -> Outcome:
    """The question kept with its verdicts, or dropped with the reason of the first check it failed."""
    index, prompts, models = context
    verdicts: list[Verdict] = []
    problem = rule_problem(question.question, question.quote, question.category)
    problem = problem or CATEGORIES[question.category].check(question.question, question.quote, offer, index)
    earlier = duplicate_of(question, kept)
    if problem is None and earlier is not None:
        problem = f"a duplicate of question {earlier.id}"
    if problem is not None:
        return _drop(
            question, _reason_of(problem, earlier), [Verdict("code rules", passed=False, reason=problem)]
        )
    verdicts.append(
        Verdict("code rules", passed=True, reason="quote found verbatim; rules and category check passed")
    )
    for check, template_name, values, wanted in _judge_checks(question, offer, index):
        reply = _ask_judge(models, prompts[template_name], values)
        verdict = _verdict(check, reply, models.judge_name, passing=wanted)
        verdicts.append(verdict)
        if not verdict.passed:
            return _drop(question, f"not {check} (judge)", verdicts)
    return _closed_book(question, prompts, models, verdicts)


def _reason_of(problem: str, earlier: Question | None) -> str:
    if earlier is not None and problem.startswith("a duplicate"):
        return "duplicate"
    if problem.startswith(("the quote", "the question has")):
        return "code rules"
    return "not of its category"


JudgeCheck = tuple[str, str, dict[str, str], bool]  # check, prompt, values, the verdict that passes


def _judge_checks(question: Question, offer: Offer, index: CorpusIndex) -> list[JudgeCheck]:
    values = {"question": question.question, "quote": question.quote}
    checks: list[JudgeCheck] = []
    category = CATEGORIES[question.category]
    if category.JUDGE:
        twin = index.text(offer.twin) if offer.twin else ""
        wanted = getattr(category, "JUDGE_WANTS", True)
        checks.append(
            (f"of its category ({question.category})", category.JUDGE, {**values, "twin": twin}, wanted)
        )
    checks.append(("valid", "judge.validity", values, True))
    return checks


def _ask_judge(models: Models, template: str, values: dict[str, str]) -> JudgeReply:
    """One judge call, asked again once when the reply cannot be read (design §6.6)."""
    reply = read_verdict(models.judge(fill(template, **values)))
    if reply.passed is None:
        reply = read_verdict(models.judge(fill(template, **values)))
    return reply


def _verdict(check: str, reply: JudgeReply, judge: str, *, passing: bool) -> Verdict:
    """A verdict: it passes when the judge said ``passing``; an unreadable reply keeps the question."""
    if reply.passed is None:
        return Verdict(
            check, passed=True, reason=f"judge reply unreadable twice ({reply.reason}); kept", by=judge
        )
    return Verdict(check, passed=reply.passed is passing, reason=reply.reason, by=judge)


def _closed_book(
    question: Question, prompts: dict[str, str], models: Models, verdicts: list[Verdict]
) -> Outcome:
    check = "answerable without documents"
    answer = models.answer(fill(prompts["answer.closed_book"], question=question.question))
    if is_unknown(answer):
        verdicts.append(Verdict(check, passed=True, reason="the writer answered UNKNOWN; no judge call"))
        return _keep(question, verdicts)
    values = {"question": question.question, "quote": question.quote, "answer": answer}
    reply = _ask_judge(models, prompts["judge.closed_book"], values)
    # "correct" means the answer states the fact without the documents: the question is too easy.
    verdict = _verdict(check, reply, models.judge_name, passing=False)
    verdicts.append(replace(verdict, reason=f"answered {answer[:120]!r}: {verdict.reason}"))
    if not verdict.passed:
        return _drop(question, "answerable without the documents (judge)", verdicts)
    return _keep(question, verdicts)


def _keep(question: Question, verdicts: list[Verdict]) -> Question:
    return replace(question, verdicts=tuple(verdicts))


def _drop(question: Question, reason: str, verdicts: list[Verdict]) -> Dropped:
    return Dropped(
        question.category, reason, question.question, question.quote, tuple(verdicts), question.offer
    )
