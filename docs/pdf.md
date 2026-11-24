# PDF documents

```text
pip install 'ragcourt[pdf]'
```

With this extra, every `.pdf` in your folder is a document. Its text is what
[pypdf](https://pypi.org/project/pypdf/) extracts, page by page, with a blank line between pages. ragcourt
changes nothing else in it, so a gold quote is an exact quote of that text, and every chunker is given the
same text.

**Look at the text before you trust a result.** PDF stores where letters are drawn on a page, not sentences,
so every extractor guesses:

```text
ragcourt audit docs/ --show manual.pdf      # the text ragcourt was given, with the chunk boundaries
```

| What you may see | Why | What to do |
|---|---|---|
| lines of two columns mixed together | the page has columns and the extractor read across them | convert the PDF with a layout-aware tool and give ragcourt the text |
| `docu-` at a line end, `ment` on the next | the PDF broke the word; ragcourt does not re-join it | the audit's `cut.mid_sentence` shows how often chunks end there |
| the same header or page number between pages | it is printed on every page | expect a few questions about it to be dropped; cut it with your own tool if it matters |
| tables as loose words | a PDF table is positioned text, not a table | convert it to Markdown or HTML if tables matter |

If your own system extracts PDF text another way, give ragcourt **that** text (save it as `.txt` or `.md`):
then ragcourt measures what your system really sees.

**Skipped, with the reason** (listed by every command, never guessed):

| Reason | Meaning |
|---|---|
| `install 'ragcourt[pdf]' to read PDF` | the extra is not installed |
| `no text in this PDF (scanned pages?): run OCR first` | the pages are pictures |
| `encrypted PDF; remove its password first` | it has a password |
| `damaged or not a PDF (…); convert it to text` | it could not be parsed |
| `PDF over 50 MB` / `over 5000 pages` | split it or convert it |

Nothing inside a PDF (scripts, forms, attachments) is ever run or opened, and nothing is sent anywhere to
read it.
