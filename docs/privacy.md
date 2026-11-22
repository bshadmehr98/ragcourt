# Privacy

With no configuration, the only address ragcourt contacts is Ollama on this machine
(`http://localhost:11434`, or `ollama_url`). An endpoint is contacted only when you configure it, and then
only for the models you name with `endpoint:NAME/MODEL`. No telemetry, no update check.

| Call | Sent | To |
|---|---|---|
| embed (audit, rank, doctor) | chunk texts, questions, quotes (one text per call through Ollama) | the embedder's server |
| write a question | one passage of a document (about 2,000 characters), or two for a distractor | the writer's server |
| closed-book answer | the question only | the writer's server |
| judge | the question, its quote, the closed-book answer, for a distractor the other passage | the judge's server |
| `llm` reranker | a question and up to 20 chunk texts | the reranker's server |
| `endpoint` reranker | a question and the candidate chunk texts | the endpoint |
| doctor | samples of up to 8 documents, 4,000 characters each | the doctor's server |
| setup | model names (list, show, pull after your yes) | Ollama |

Keys are read from the environment variable `api_key_env` names, sent only in an `Authorization`
header, and never written to any file or message. Document text never goes to logs.

Everything ragcourt keeps is in `.ragcourt/` as plain files (see [cli.md](cli.md)): questions with their
quotes (which are text of your documents), cached vectors, run results. Do not commit `.ragcourt/` from a
private corpus. Code a model writes runs only after you approve its exact hash, in a separate process with
a timeout and an environment without your keys; that is isolation, not a sandbox.
