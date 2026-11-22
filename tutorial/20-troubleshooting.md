# 20. Troubleshooting

| You see | It means | Do |
|---|---|---|
| `Ollama does not answer at http://localhost:11434` | Ollama is not running (checked before a run starts) | start it (`ollama serve`), or set `ollama_url` |
| `… could not be reached: [Errno 111] Connection refused` | a server stopped answering during a run | start it again, then `--resume` |
| `Not installed in Ollama: …` | a run needs a model Ollama doesn't have (checked before any question is written) | `ollama pull NAME`, or `ragcourt models set ROLE MODEL` |
| `… is not installed. Pull it now?` | `models set` names a model Ollama doesn't have | answer yes; with no, `ragcourt.toml` is left unchanged |
| `Score 80% on 40 labelled cases (90% needed): FAILED.` | the judge model is not reliable enough | a larger judge: `ragcourt models set judge gemma4` |
| `No documents to rank` / `No documents to audit` | the folder has no `.md`, `.txt`, `.rst` or `.html` files | check the path; convert PDFs to text; the skipped files are listed with why |
| `skipped …: not valid UTF-8` | a file in another encoding | save it as UTF-8 |
| `Another ragcourt (process N) is using …` | a second ragcourt in the same working folder | wait, or use another `--workdir`; delete the `lock` file if no other ragcourt runs |
| `Note: on held-out questions … is separably better than this choice` | the dev questions were too few to see a difference the held-out ones see | prefer that pipeline, or write more questions (`--questions 150`) |
| `… redirected (301) to …` | an endpoint's address moved | put the new address in `base_url` |
| `too few to choose on some and report on others` | not enough questions survived | more per kind: `--questions 30`, or more documents |
| `too few to rank (N held-out questions)` | that kind has fewer than 30 held-out questions | more questions, or accept it: it is left out of the overall |
| `No significant difference … no winner` | the entries can't be told apart on these questions | pick the cheaper, or write more questions to see smaller differences |
| `estimated` next to sizes | the embedder didn't answer; sizes are characters / 4 | start Ollama for measured sizes |
| `Chunker … returned chunk N of …, which is not in the source` | your chunker changed the text | return text from the document unchanged (chapter 3) |
| `over the budget` (exit 4) | a budget stopped the run | `--resume`, with a larger `--budget-minutes` if needed |
| `A money budget is set but an endpoint has no price` | ragcourt can't estimate the cost | add it to `[prices]` |
| `unknown setting … The settings are: …` | a typo in `ragcourt.toml` | use a name from the list |
| `No unfinished run has this plan … starting a new one` | `--resume` found no stopped run with the same documents, models and settings | expected after a change; the new run reuses questions and embeddings |
| the first run is slow | writing ~540 questions takes 15 to 25 min on an 8 GB GPU | try `--questions 20` first; later runs reuse the questions |
| a distractor column always too few | your documents have few look-alike passages | normal for small or very varied document sets |

## Making runs faster

- Fewer questions while you explore: `--questions 20`, then the full set for the decision.
- Compare less: `--embedders nomic-embed-text --chunkers "markdown;recursive:size=256,overlap=32"`.
- Later runs reuse questions and embeddings: only new chunkers or embedders cost time.
- A smaller writer and judge (`qwen3:4b`) are faster but must pass the judge's self-test.

## Getting help

`ragcourt COMMAND --help` says what a command calls and sends. To report a problem, include the command,
the output, and `ragcourt --version`; never your documents or `.ragcourt/` if they are private.

Next: [glossary](21-glossary.md).
