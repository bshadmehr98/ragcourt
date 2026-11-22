# 8. Test questions and gold answers

To measure retrieval you need questions whose right answers you know. ragcourt writes them from your
documents with a local model, and checks them hard.

## Gold answers are exact quotes

Every question comes with a **gold quote**: one to three sentences copied from your document that answer
it. ragcourt finds the quote in the document by code (exactly, or with spaces and line breaks ignored); a
quote that is not found drops the question. So the gold answer is a **span** of your text (a start and an
end position), not a chunk. That matters: every chunker is judged on the same questions, because none of
them is tied to one way of cutting.

A chunk **hits** a question when it holds the whole quote.

## Six kinds of questions

One mixed set of questions cannot tell you *what* an embedder is bad at. ragcourt writes six kinds, each
aimed at a known weakness:

| Kind | Example | Tests | How ragcourt checks it is really that kind |
|---|---|---|---|
| `paraphrase` | "How long until a failed job is tried again?" → "The first retry waits 10 seconds" | meaning, not words | the question shares almost no words with the quote |
| `keyword` | "retry delay seconds" | a search-box query | 2 to 6 words, no question mark |
| `exact_term` | "What does LARKSPUR_MAX_INFLIGHT limit?" | rare names, identifiers, numbers with units, which embedders blur | the term (found in one document only, chosen by code) is in the question and the quote |
| `distractor` | worded with the vocabulary of a similar passage that does *not* answer it | being misled by a look-alike | uses two of that passage's own words; the judge confirms that passage does not answer it |
| `negation` | "Which jobs are never retried?" | "not", "never", exceptions | a negation in question and quote; the judge confirms |
| `numeric` | "What is the default job timeout?" | numbers, defaults, limits, dates | the quote states a number; the judge confirms it is the one asked |
| `user` | your own questions | what you care about | the quote is found (chapter 14) |

The passages offered for each kind are chosen by code: a `negation` question is only asked about passages
that contain a negation, a `distractor` only about pairs of similar passages from different documents.
Headers and footers repeated across your documents are never offered.

## How many

90 per kind by default, about 540 in all. One third of each kind is **dev**: used to choose between
pipelines. Two thirds are **held-out**: every number you see is computed on them. Choosing and reporting on
different questions keeps the reported numbers honest (chapter 11). The split comes from a hash of each
question, so it never changes between runs.

A kind with fewer than 30 held-out questions is shown as **too few to rank** and left out of the overall
score. Small document sets often can't support every kind (there may be no similar passages for
distractors), and ragcourt says so rather than guess.

## Every question is checked, in order

1. **Quote found verbatim** in the document.
2. **Code rules**: the quote has at least 6 words, is a sentence (not a bare name or a line of code), is at
   most 120 tokens; the question has at least 3 words (except keyword searches).
3. **Of its kind** (the table above).
4. **Not a duplicate** of an earlier question.
5. **Valid** (the judge): a real question, answered by the quote on its own.
6. **Not answerable from memory** (the judge): the writer answers it *without* your documents. If that
   answer already states the quote's fact, the question tests the model's memory, not your retrieval, and
   it is dropped. An answer of "UNKNOWN" keeps it.

Every drop is counted by reason, and every verdict keeps its reason:

```text
ragcourt questions my_docs/                     # write them alone (rank does it for you)
ragcourt questions show                         # every kept question, quote and verdicts
ragcourt questions show --dropped --reason judge
```

Writing ~540 questions takes 15 to 25 minutes on an 8 GB GPU, once: they are saved in
`.ragcourt/questions.jsonl` and reused while your documents and models don't change. If the run is
interrupted, it continues where it stopped.

Next: [the judge](09-the-judge.md).
