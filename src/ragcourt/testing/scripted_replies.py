"""A deterministic stand-in for the writer and the judge: replies computed from the prompt (§15.2).

It reads the prompt ragcourt sends and answers the way a careful model would, so the whole question
pipeline runs offline: the writer copies a sentence of the passage as its quote and words a question for
the category; the closed-book answerer says UNKNOWN unless told it knows; the judge answers the labelled
self-test cases correctly (or, as a ``lenient`` judge, grades refusals as correct) and otherwise passes
questions unless told to fail them. Use it as the ``reply`` of ``fake_ollama`` or with ``ScriptedModel``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from ragcourt.io.prompts import judge_cases

FIELD = re.compile(r'(PASSAGE|OTHER passage[^:]*):\n"""(.*?)"""', re.DOTALL)
SENTENCE = re.compile(r"[^.!?\n]*[A-Za-z][^.!?\n]*[.!?]")
CODE_WORDS = (
    "alpha",
    "bravo",
    "charlie",
    "delta",
    "echo",
    "foxtrot",
    "golf",
    "hotel",
    "india",
    "juliet",
    "kilo",
)
NEGATION = re.compile(r"\b(not|never|no|without|except|unless|cannot)\b", re.I)


@dataclass
class ScriptedReplies:
    """Replies by prompt kind; the sets name question texts (substrings) that get special answers."""

    known: set[str] = field(default_factory=set[str])  # questions the writer answers without documents
    invalid: set[str] = field(default_factory=set[str])  # questions the judge calls invalid
    lenient: bool = False  # a judge that grades refusals and generic answers as correct
    unverbatim: bool = False  # a writer whose quotes are not in the passage
    calls: list[str] = field(default_factory=list[str])

    def __call__(self, prompt: str) -> str:
        """The reply to one prompt."""
        self.calls.append(prompt.split("\n", 1)[0])
        if prompt.startswith("You write one"):
            return self._write(prompt)
        if prompt.startswith("Answer the question below"):
            return self._answer(prompt)
        return self._judge(prompt)

    def _write(self, prompt: str) -> str:
        fields = dict(FIELD.findall(prompt))
        passage, twin = fields.get("PASSAGE", ""), next((v for k, v in fields.items() if k != "PASSAGE"), "")
        term = _after(prompt, "written exactly like this: ")
        quote = _pick_sentence(passage, prompt, term)
        if self.unverbatim:
            quote = "This sentence was invented and is not in the passage at all."
        return json.dumps({"question": _question(prompt, quote, term, twin), "quote": quote})

    def _answer(self, prompt: str) -> str:
        question = _after(prompt, "Question: ")
        if any(text in question for text in self.known):
            return "I know this one: it is exactly what the documentation says."
        return "UNKNOWN"

    def _judge(self, prompt: str) -> str:
        case = _labelled_case(prompt)
        if case is not None:
            return _verdict(self._case_verdict(case))
        question = _after(prompt, "QUESTION: ")
        if prompt.startswith("You grade an answer"):
            answer = _after(prompt, 'ANSWER: """')
            knows = "UNKNOWN" not in answer and any(text in question for text in self.known)
            return _verdict("correct" if knows else "incorrect")
        if any(text in question for text in self.invalid):
            return _verdict("no")
        return _verdict("yes")

    def _case_verdict(self, case: dict[str, str]) -> str:
        if self.lenient and case["kind"] in ("refusal", "generic", "guess"):
            return "correct"
        return case["expected"]


def _after(prompt: str, marker: str) -> str:
    start = prompt.find(marker)
    return prompt[start + len(marker) :].split("\n", 1)[0].strip().strip('"') if start >= 0 else ""


def _pick_sentence(passage: str, prompt: str, term: str) -> str:
    sentences = [
        match.group(0).strip() for match in SENTENCE.finditer(passage) if len(match.group(0).split()) >= 6
    ]
    wanted = sentences
    if term:
        wanted = [sentence for sentence in sentences if term in sentence]
    elif "does NOT do" in prompt:
        wanted = [sentence for sentence in sentences if NEGATION.search(sentence)]
    elif "answer is a number" in prompt:
        wanted = [sentence for sentence in sentences if re.search(r"\d", sentence)]
    return (wanted or sentences or [passage.strip()[:200]])[0]


def _question(prompt: str, quote: str, term: str, twin: str) -> str:
    words: list[str] = re.findall(r"[A-Za-z]{4,}", quote)
    if twin:
        twin_words = [word for word in re.findall(r"[A-Za-z]{5,}", twin) if word not in quote]
        return f"How do {' and '.join(twin_words[:3])} work together here?"
    templates = [
        ("keyword search", " ".join(words[:3])),
        ("does NOT do", f"What is never allowed or not done regarding {' '.join(words[:2])}?"),
        ("answer is a number", f"Which number is given for {' '.join(words[:2])}?"),
    ]
    if term:
        return f"What does the documentation say about {term}?"
    for marker, question in templates:
        if marker in prompt:
            return question
    # Words of no passage, varied by the quote, so paraphrases neither copy the quote nor repeat each other.
    marker = CODE_WORDS[sum(map(ord, quote)) % len(CODE_WORDS)]
    return f"Which statement covers the {marker} matter, in other terms?"


def _labelled_case(prompt: str) -> dict[str, str] | None:
    question = _after(prompt, "QUESTION: ")
    answer = _after(prompt, 'ANSWER: """') if "ANSWER:" in prompt else None
    quote = _after(prompt, 'QUOTE: """')
    check = "closed_book" if prompt.startswith("You grade an answer") else "validity"
    for case in judge_cases():
        same = (
            case["check"] == check and case["question"] == question and case["quote"].startswith(quote[:40])
        )
        if same and (answer is None or case.get("answer", "").startswith(answer[:40])):
            return {key: str(value) for key, value in case.items()}
    return None


def _verdict(verdict: str) -> str:
    return json.dumps({"verdict": verdict, "reason": f"scripted: {verdict}"})
