# Security

## Reporting a vulnerability

Please report security problems privately, through GitHub's **Report a vulnerability** button on the
repository's Security tab (private vulnerability reporting), not in a public issue. Say what you found,
how to reproduce it and what it lets someone do. You will get an answer within a week; a fix and an
advisory follow as soon as the fix is out.

## What ragcourt promises, and what it does not

- With no configuration it contacts only Ollama on `localhost`. A model server elsewhere is contacted only
  when you configure it as an endpoint. No telemetry.
- API keys are read only from the environment variable you name, sent only in a request header to the
  address you configured (redirects are refused), and never written to a file or a message. Over plain
  `http://` a key travels unencrypted: use `https://` for a server not on your machine or network.
- Text from your documents and from models is shown on the terminal with control characters escaped, and
  written into `report.html` escaped; the report fetches nothing.
- Code a model writes (`ragcourt doctor`) runs only after you approve its exact SHA-256, in a separate
  process with a time limit, an output limit and an environment without your keys. **That is isolation,
  not a sandbox**: the code can still read your files. Read it before you approve it.
- `ragcourt.toml` and the `.py` files in `ragcourt_stages/` of the folder you run ragcourt in are your
  configuration and your code: they choose servers and run as Python. Run ragcourt from a folder you
  trust, beside the documents you downloaded, not inside them.
- `.ragcourt/` holds questions and quotes, which are text of your documents. Don't commit it for private
  documents.

Supported versions: the latest release.
