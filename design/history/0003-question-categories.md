# 0003: Can a local model write each kind of question? (2026-11-22)

The owner asked for many questions of each kind, "60 questions with different wording, 60 misleading
questions, 60 questions that contain specific words, which we know embedding systems are bad at", since a
few dozen mixed questions cannot say which embedder is better at what. Before designing the categories,
this note tries them with `gemma4` on the owner's machine. Script: [`0003-question-categories.py`](0003-question-categories.py).
Evidence levels as in [0000-research.md](0000-research.md).

## Method

The same corpus as [0002](0002-local-models.md) (hone-flow's `docs/`, 14 pages). 8 paragraphs longer
than 300 characters, sampled with a fixed seed; for each of six categories, one request per paragraph
asking for one question of that category with a verbatim quote. Then two checks by code: the quote is
found in the paragraph, and the question is of the category it was asked for:

| Category | Asked for | Checked by code |
|---|---|---|
| `paraphrase` | different words from the passage | content-word overlap of question and quote (Jaccard) below 0.15 |
| `keyword` | 2 to 5 search terms | 2 to 6 words, no question mark |
| `exact_term` | must contain a given rare term of the passage | the term is in the question and the quote |
| `negation` | about what something does not do, or an exception | a negation word in the question and in the quote |
| `numeric` | a number, default, limit, version or date | a digit in the quote |
| `distractor` | worded with the vocabulary of the most similar other paragraph, which does not answer it | the question shares more words with the other paragraph than with its own |

## Results

| Category | Quote found | Category confirmed by code | Seconds per request |
|---|---|---|---|
| `paraphrase` | 8 / 8 | 7 / 8 | 1.1 |
| `keyword` | 7 / 8 | 7 / 8 | 0.4 |
| `exact_term` | 8 / 8 | 3 / 8 | 0.6 |
| `negation` | 8 / 8 | 1 / 8 | 0.6 |
| `numeric` | 7 / 8 | 3 / 8 | 0.5 |
| `distractor` | 8 / 8 | 2 / 8 | 0.6 |

`measured`. Reading the failures (`inferred`):

- **The model does not reliably obey the category.** Asked for a negation, it writes "what does X NOT do"
  about a passage that states no negation; asked for a number, it asks for a default the passage does not
  give. Without the code checks these would have been counted as hard questions and would have blamed the
  embedders for the model's mistakes.
- **The passage decides what is possible.** Most failures came from passages that had no negation, no
  number or no truly rare term. Choosing, by code, passages that can support the category (a negation in
  the text, a number, an identifier that appears in one document only, a paragraph with a near twin)
  should raise the yield far more than a better prompt.
- **The rare term must be chosen better.** "Rare" by document frequency alone picked ordinary words
  ("reproduce", "both"); identifiers, names, numbers with units and code tokens are what embedders are known
  to miss.
- **Distractors need a real twin.** Only 2 of 8 questions leaned towards the other paragraph; the pairs
  with high overlap were the ones that worked.
- **Yield sets the cost.** With a yield of 1 to 3 in 8 for the hard categories, 90 questions of one
  category may need 250 or more requests: about 3 minutes each on this machine, so 15 to 25 minutes for a
  full set, once per corpus (questions are reused). A small corpus may not hold 90 good questions of
  every category at all; that has to be reported, not hidden.

## Not measured

Yield after passage selection by code; the judge's agreement on category membership; other corpora and
other models.
