# 11. Intervals, ties and "too few to rank"

A score like 0.62 is an average over a few dozen questions. With other questions of the same kind it could
have been 0.55 or 0.70. ragcourt never shows a number without saying how sure it is, and never names a
winner the numbers cannot support.

## Dev and held-out

Questions are split once: one third **dev**, two thirds **held-out** (chapter 8). The search *chooses* on
dev questions and *reports* on held-out ones. Why: if you pick the best of ten pipelines on some
questions, its score on those same questions is flattered by luck. Measured on questions that played no
part in the choice, the score is honest.

## The overall score

Each kind of question gets its own mean; **overall** is the mean of those means. So every kind weighs the
same, whether it has 60 questions or 35.

## The 95% interval: `0.62 [0.50, 0.78]`

ragcourt uses the **bootstrap**: it draws the held-out questions again, at random, with replacement, as
many as there are (so some appear twice and some not at all), and recomputes the score. It does this 2,000
times. The middle 95% of those scores is the interval. Read it as: "with other questions like these, the
score would most likely be between 0.50 and 0.78". A wide interval means few questions or very mixed
results. The draws use a fixed seed, so the same run gives the same interval.

## Ties: "no significant difference"

Two pipelines' intervals overlapping does not by itself say much, because both were measured on the same
questions. So ragcourt compares the top two **paired**: for each bootstrap draw, it takes the *difference*
between them on the same drawn questions. If the 95% interval of that difference contains 0, the two
cannot be told apart. The output then says

```text
No significant difference between A and B: no winner.
```

and marks with `=` every entry the top cannot be told apart from. This is the most common honest answer
on small document sets, and it is useful: it means "pick the cheaper one".

**Smallest difference** (printed per kind): half the width of that paired interval. Differences smaller
than this cannot be seen with these questions; to see them, write more questions (`--questions 150`).

**Leaders per kind**: when another entry is clearly better on one kind of question, even if not overall,
the output says so: "On paraphrase, … dense leads."

## Too few to rank

A kind with fewer than 30 held-out questions (`min_held_out`) is printed with its count ("exact_term: too
few to rank (1 held-out questions)") and left out of the overall score. If *every* kind is too few, the
board is marked **indicative** and names no winner. Small document sets often produce few distractor or
exact-term questions; ragcourt says so rather than guess.

## When the search picks among ties

The search still has to carry one pipeline into its next step. Among entries tied on dev, it keeps the
cheaper one (in money: local models cost nothing), then the one sending fewer tokens to the language
model per question, then the first listed, and says so:

```text
Chosen for the next step (on dev questions): … (tied on dev with 2 more; kept the cheaper, then smaller, then first listed)
```

Next: [ranking pipelines](12-ranking.md).
