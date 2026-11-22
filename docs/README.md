# ragdoctor documentation

The user documentation is written as the first design is built. The design itself is in
[`../design/`](../design/README.md); start with [`../design/current.md`](../design/current.md).

| Page | What it will hold |
|---|---|
| [`cli.md`](cli.md) | the `ragdoctor` command line: `audit`, `rank`, `explain`, `doctor`, the configuration file, the results file |
| [`audit.md`](audit.md) | every audit check, its code, what triggers it and what to do about it |
| [`questions.md`](questions.md) | how questions and gold quotes are made and filtered, the dev and held-out split, bringing your own questions, the question file |
| [`metrics.md`](metrics.md) | every metric, how it is computed, the confidence intervals and what "no significant difference" means |
| [`stages.md`](stages.md) | the built-in stages, the extras, and how to write your own stage in one file |
| [`one-question.md`](one-question.md) | one question followed from the document to the blame |
| [`privacy.md`](privacy.md) | what is read, what is sent to which endpoint, what is stored where, no telemetry |
