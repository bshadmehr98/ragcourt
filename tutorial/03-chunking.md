# 3. Chunking: cutting documents into pieces

A retriever does not return whole documents; it returns **chunks**, pieces of a few hundred words. A
chunker decides where to cut. Too big, and the answer is drowned in unrelated text (and may run past what
the embedder can read). Too small, and the answer loses its context or is cut in half.

## Sizes are counted in tokens

A **token** is roughly a word or a punctuation mark. ragcourt's built-in chunkers count *reference
tokens*: words and punctuation, the same for every embedder, so chunkers compare fairly. (Embedding models
count their own tokens, usually a little more; the audit shows sizes in those, chapter 4.)

## The built-in chunkers

Here is one short document cut by each of the four built-in chunkers:

```python
from ragcourt import stages

stages.load_builtins()
text = """# Retries

When a job fails, Larkspur tries it again later. The first retry waits 10 seconds, and each later retry waits three times as long.

## Errors that are not retried

A job that raises Abort is never retried. Jobs whose arguments cannot be decoded are not retried either.
"""
fixed = stages.find("chunker", "fixed").function(text, size=20, overlap=0)
recursive = stages.find("chunker", "recursive").function(text, size=30, overlap=0)
markdown = stages.find("chunker", "markdown").function(text, size=60, overlap=0)

assert fixed[0].endswith("waits 10 seconds,")  # cut in the middle of a sentence
assert recursive[1].startswith("## Errors")  # cut at the paragraph boundary
assert markdown[1].startswith("## Errors that are not retried")  # one section per heading
```

| Chunker | How it cuts | Good for | Watch out |
|---|---|---|---|
| `fixed` (`size=256, overlap=32`) | every `size` tokens, ignoring the text's shape | uniform text without structure | cuts sentences, tables and code anywhere |
| `recursive` (`size=512, overlap=64`) | tries paragraphs first, then sentences, then lines, then words, and packs pieces up to `size` | most prose | a section can lose its heading |
| `sentence` (`size=256`) | whole sentences packed up to `size`; never cuts a sentence | short factual text | one very long sentence can pass `size` |
| `markdown` (`size=512, overlap=64`) | one chunk per section (heading kept at its start), cut like `recursive` inside long sections | documentation with headings | many tiny chunks when sections are short |
| `chonkie.token`, `chonkie.sentence`, `chonkie.recursive` | the chonkie library's chunkers | comparing with chonkie | `pip install 'ragcourt[chonkie]'` |
| `langchain.recursive`, `langchain.markdown` | LangChain's text splitters (sizes in characters) | comparing with LangChain | `pip install 'ragcourt[langchain]'` |
| your own | any function from text to a list of strings | your documents' quirks | chapter 16 |

## Parameters

A chunker and its parameters are written as one **spec**: `name:key=value,key=value`, for example
`recursive:size=256,overlap=32`. A misspelled parameter is an error that lists the right ones.

- **size**: the largest chunk, in tokens.
- **overlap**: how many tokens a chunk repeats from the end of the one before, so an answer cut at a
  boundary is still whole in one of them. Costs more chunks and more embedding.

## One rule every chunker must follow

A chunker must return text that is in the document, unchanged. ragcourt finds where each chunk sits in the
source (exactly, or with differences in spaces and line breaks ignored), because it judges every chunker
against the same gold quotes (chapter 8). A chunker that adds text (a summary, a title prefix) cannot be
measured, and fails with an error naming the chunk.

## Choosing

You don't choose by guessing: `ragcourt rank` measures every chunker in `[search] chunkers` on your
documents (chapter 12), and `ragcourt audit` shows how each one cuts them (chapter 4).

Next: [the audit](04-audit.md).
