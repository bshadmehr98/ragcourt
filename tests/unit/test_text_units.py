"""Reference units (design §4.3, D-009)."""

from ragcourt.text_units import (
    count_tokens,
    ends_sentence,
    estimate_tokens,
    sentence_spans,
    strip_span,
    token_spans,
    tokens_between,
)


def test_tokens_are_words_and_punctuation() -> None:
    assert count_tokens("Wait 10 s, then retry.") == 7
    assert token_spans("a, b") == [(0, 1), (1, 2), (3, 4)]


def test_the_estimate_is_characters_over_four_rounded_up() -> None:
    assert [estimate_tokens(text) for text in ("", "abc", "abcd", "abcde")] == [0, 1, 1, 2]


def test_tokens_between_counts_starts_in_a_span() -> None:
    starts = [start for start, _ in token_spans("one two three four")]
    assert tokens_between(starts, 0, 7) == 2
    assert tokens_between(starts, 4, 100) == 3


def test_sentences_split_after_closing_punctuation_and_quotes() -> None:
    text = 'One. "Two?" Three! (Four.) five'
    spans = sentence_spans(text)
    assert [text[s:e] for s, e in spans] == ["One.", '"Two?"', "Three!", "(Four.)", "five"]


def test_sentences_of_a_part_of_the_text() -> None:
    text = "skip. A b. C d."
    assert [text[s:e] for s, e in sentence_spans(text, 6, len(text))] == ["A b.", "C d."]


def test_strip_span_and_sentence_ends() -> None:
    assert strip_span("  ab  ", 0, 6) == (2, 4)
    assert ends_sentence("Done.  ") and ends_sentence("a list:") and ends_sentence("(see this)")
    assert not ends_sentence("and the") and not ends_sentence("   ")
