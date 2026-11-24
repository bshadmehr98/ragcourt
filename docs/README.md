# ragcourt documentation

New here? Start with [the tutorial](../tutorial/README.md): RAG retrieval and ragcourt from zero, in 21
short chapters. These pages are the short reference behind it. The design behind every
behaviour is in [`../design/current.md`](../design/current.md).

| Page | What it holds |
|---|---|
| [`cli.md`](cli.md) | every command and option, exit codes, the files ragcourt writes |
| [`models.md`](models.md) | the model roles, the defaults and why, `setup`, `models set`, endpoints, prefixes and input limits |
| [`audit.md`](audit.md) | every audit check: what triggers it, its near miss, what to do |
| [`questions.md`](questions.md) | the question categories, how questions and quotes are written and filtered, the split, your own questions |
| [`judge.md`](judge.md) | what the judge is asked and shown, what it never decides, its prompts and self-test, reading its verdicts |
| [`metrics.md`](metrics.md) | every metric, the intervals, "no significant difference", too few to rank |
| [`blame.md`](blame.md) | why a question was missed: the stages, the mechanisms, the probes, confirmed or indicated, fixes |
| [`stages.md`](stages.md) | the built-in stages, the extras, and how to write your own stage in one file |
| [`one-question.md`](one-question.md) | one question followed from its document to its blame |
| [`pdf.md`](pdf.md) | reading PDF with the extra `pdf`: what the text looks like, what is skipped and why |
| [`privacy.md`](privacy.md) | what is read, what is sent to which address, what is stored where |
