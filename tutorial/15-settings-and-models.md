# 15. Settings and models

Every setting lives in `ragcourt.toml` in the folder you run from, and every line is optional. A
misspelled key is an error that lists the right ones. Where a value comes from, in order: a command-line
flag, then `ragcourt.toml`, then the built-in default. Every plan prints which one applied.

## The five model roles

| Role | Does | Is shown | Default |
|---|---|---|---|
| `writer` | writes questions and copies a quote that answers each | one passage at a time | `gemma4` |
| `judge` | filters questions (chapter 9) | a question, its quote, an answer | `gemma4` |
| `embedders` | the embedding models compared | your chunks and questions | `nomic-embed-text`, `embeddinggemma`, `mxbai-embed-large` |
| `reranker` | the chat model of the `llm` reranker | a question and 20 chunks | `gemma4` |
| `doctor` | describes your documents, suggests a chunker | samples of your documents | `gemma4` |

Defaults were chosen by measurement on an 8 GB GPU: `gemma4` copied 19 of 20 quotes exactly and scored 98%
as a judge.

```text
ragcourt models                                  # what each role uses now, and why
ragcourt models set judge qwen3:4b               # pulls it if you agree, tests it
ragcourt models set embedders nomic-embed-text,bge-m3,qwen3-embedding:0.6b
ragcourt rank my_docs/ --judge qwen3:4b          # for one run only
```

```python
import tempfile
from pathlib import Path

from ragcourt.cli import main
from ragcourt.testing import offline_project

with tempfile.TemporaryDirectory() as folder, offline_project(Path(folder)) as server:
    server.models["another-judge"] = 4096
    assert main(["models", "set", "judge", "another-judge", "-q"]) == 0
    assert 'judge = "another-judge"' in (Path(folder) / "ragcourt.toml").read_text()
```

Changing the writer, judge or a prompt means a new question set; changing embedders or chunkers does not.

## A whole `ragcourt.toml`, with the defaults

```text
seed = 0                                   # every random choice
ollama_url = "http://localhost:11434"
stages_dir = "ragcourt_stages"             # your own stages (chapter 16)
# prompts_dir = "my_prompts"               # your own versions of the prompts

[models]
writer = "gemma4"
judge = "gemma4"
embedders = ["nomic-embed-text", "embeddinggemma", "mxbai-embed-large"]
reranker = "gemma4"
doctor = "gemma4"

[questions]
per_category = 90                          # questions per kind
categories = ["paraphrase", "keyword", "exact_term", "distractor", "negation", "numeric"]
min_held_out = 30                          # fewer held-out questions: "too few to rank"
window_chars = 2000                        # size of the passages shown to the writer
max_requests_per_question = 6              # give up on a kind after this many tries per question

[search]
chunkers = ["recursive:size=512,overlap=64", "recursive:size=256,overlap=32", "sentence:size=256",
            "markdown:size=512,overlap=64", "fixed:size=256,overlap=32"]
retrievers = ["dense", "bm25", "hybrid"]
rerankers = ["llm"]
metric = "recall_at_budget"
k = 5                                      # chunks a language model reads
depth = 50                                 # chunks retrieved
budget_tokens = 400                        # the budget of recall_at_budget
resamples = 2000                           # bootstrap draws

[audit]
tiny_tokens = 20
near_duplicate_jaccard = 0.9
repeated_line_share = 0.3                  # a line in this share of documents is boilerplate
boilerplate_share = 0.5                    # a chunk this much boilerplate is flagged

[budget]
minutes = 60                               # no default: unlimited
usd = 2                                    # no default: unlimited
```

## Endpoints: models outside Ollama

Any OpenAI-compatible server (a hosted API, vLLM, llama.cpp, LM Studio):

```text
[endpoints.openai]
base_url = "https://api.openai.com/v1"
api_key_env = "OPENAI_API_KEY"             # the NAME of an environment variable, never the key

[models]
embedders = ["nomic-embed-text", "endpoint:openai/text-embedding-3-small"]

[prices]
"endpoint:openai/text-embedding-3-small" = 0.02   # dollars per million tokens
```

A run that costs money asks before starting, shows the estimated cost (an upper bound), and refuses to
start over `--budget-usd`. An endpoint without a price is "unknown", never zero; with a money budget set,
an unknown price refuses the run.

Next: [your own stages](16-your-own-stages.md).
