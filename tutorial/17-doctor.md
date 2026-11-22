# 17. Doctor: letting a model suggest a chunker

```text
ragcourt doctor my_docs/
```

`doctor` asks a chat model (the `doctor` role) to look at your documents and suggest how to chunk them.
Then, as everywhere in ragcourt, the suggestion is **measured**, not trusted.

## What happens

1. **Sample**: up to 8 documents (picked by size and type, with a fixed seed), each cut to about 4,000
   characters.
2. **Describe**: the model reports what it sees (headings, tables, code, lists, boilerplate, paragraph
   length) and recommends up to three built-in chunkers with parameters. A recommendation naming an
   unknown chunker or parameter is dropped and reported.
3. **Write** (skip with `--no-code`): the model may write one chunker, a Python function
   `chunk(text) -> list[str]` using only the standard library. It is saved to
   `.ragcourt/doctor/<hash>.py`.
4. **Ask**: the code is printed in full with its SHA-256, and you are asked whether to run it. It never
   runs without your yes, or `--approve SHA256` matching exactly that file:

   ```text
   ragcourt doctor my_docs/ --approve 3f9a…    # the full hash printed before
   ```

5. **Run apart**: in a separate Python process (`python -I`), in an empty temporary folder, with an
   environment without keys or proxies, one document at a time, with a time limit (10 s per document,
   `--timeout`) and an output size limit. This protects against hangs and crashes; it is **not** a security
   sandbox. Your approval is the safety step, so read the code.
6. **Validate**: the output must be a list of non-empty strings, each found in the document. Otherwise the
   chunker is rejected and the first failure is shown.
7. **Measure**: the recommendations and the written chunker join the built-in chunkers on the same
   questions. A suggestion is called **better** only when the paired interval on held-out questions says
   so; otherwise the output says "no significant difference" or "worse", with the numbers.

## Example verdicts

From the bundled example (`examples/doctor.py`), one recommended built-in chunker and one the model wrote:

```text
sentence:size=120: worse than the best baseline, fixed:size=60,overlap=0 (-0.18 [-0.30, -0.05]).
doctor-19bf2b3c: no significant difference from the best baseline, fixed:size=60,overlap=0 (+0.12 [-0.01, +0.24]).
```

The numbers are the difference from the best built-in and its paired 95% interval (chapter 11). The
first interval is all below 0: clearly worse. The second contains 0: it may be a little better, but these
questions cannot tell. The written chunker is named `doctor-<hash>` in leaderboards.

A model's opinion of your documents is a good place to start; it is not evidence. This is why every
suggestion goes through the same measurement as everything else.

Next: [files, privacy and safety](18-files-and-privacy.md).
