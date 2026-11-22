# 4. The audit: checking how chunks were cut

```text
ragcourt audit my_docs/
ragcourt audit my_docs/ --chunker "recursive:size=256,overlap=32" --chunker markdown
ragcourt audit my_docs/ --show guide.md
```

The audit cuts your documents with each chunker and checks every chunk by code. It calls no chat model and
takes seconds. With no `--chunker`, it audits the four built-in chunkers and your own.

## The eight checks

| Check | Flags a chunk that… | Why it matters | What to do |
|---|---|---|---|
| `cut.mid_sentence` | ends in the middle of a sentence the next chunk finishes | the answer may be split in two | a sentence-aware chunker, or a size that fits your paragraphs |
| `context.no_heading` | sits under a heading it does not contain | "Set it to 30" means nothing without "Timeouts" | `markdown`, or a chunker that keeps headings |
| `split.table` | holds some but not all rows of a table | the row and its column names end up apart | a larger size, or a structure-aware chunker |
| `split.code` | holds part of a code block | half an example is misleading | the same |
| `boilerplate.repeated` | is at least half lines that repeat in 30% or more of your documents (headers, footers, menus) | noise that matches many questions | remove boilerplate before chunking |
| `duplicate.near` | is 90% the same text as an earlier chunk | duplicates crowd real answers out of the top k | remove duplicates |
| `size.tiny` | has fewer than 20 tokens | too little to answer anything | merge small pieces |
| `size.over_limit` | is longer than the embedder reads | **the end of the chunk is never embedded**, silently | a smaller size, or an embedder with a longer limit |

Each check also has a near miss it must not flag: a sentence that really ends with "etc.", a chunk that
repeats its heading, a table kept whole. The thresholds are settings (`[audit]`, chapter 15).

## Sizes: measured or estimated

Sizes are counted in the **embedder's own tokens** when the embedder answers (through Ollama, each chunk's
count is the one Ollama reports): labelled **measured**. Without an embedder (Ollama is not running, say),
sizes are characters / 4 and labelled **estimated**, everywhere. The audit still runs.

**The input limit**: every embedding model reads at most a certain number of tokens and silently ignores
the rest. ragcourt measures the limit actually in force, once per model, because it can be lower than the
model advertises (chapter 5). A chunk whose measured count reaches the limit was cut and is flagged.

## Seeing the cuts

`--show guide.md` prints the document with the boundaries marked:

```text
The delay before the next attempt grows with each failure. The first retry waits 10 seconds, and each
later retry⟧ ⟦66 cut.mid_sentence context.no_heading⟧waits three times as long as the one before, …
```

`⟦66 …⟧` is where chunk 66 starts, with the checks it fails; `⟧` is where a chunk ends. Here a 40-token
`fixed` chunker cut a sentence in half and left the chunk without its heading.

## In CI

```text
ragcourt audit docs/ --fail-on split.table cut.mid_sentence
```

exits with code 3 when one of those checks fires, so a pipeline can fail the build. `--json` gives the
whole audit as data.

Next: [embeddings](05-embeddings.md).
