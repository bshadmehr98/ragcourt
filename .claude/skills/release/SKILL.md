---
name: release
description: Release a new version of ragcourt - version bump, changelog, release PR, tag that publishes to PyPI. Only when the maintainer asks for a release.
disable-model-invocation: true
argument-hint: "<version>"
---

# Release ragcourt `$ARGUMENTS`

1. `main` is up to date and clean, and CI on `main` is green (`gh run list --branch main --limit 3`).
2. `start-task` with `chore/release-<version>`.
3. The version lives only in `src/ragcourt/__init__.py` (`__version__`; `pyproject.toml` reads it).
   SemVer; while on 0.x, a breaking change bumps the minor version.
4. `CHANGELOG.md`: the unreleased section becomes `## [<version>] - <YYYY-MM-DD>`; add an empty
   unreleased section above it. Change records built in this release: `implemented in <version>`.
   If the results format, the bundled corpus or a default model changed since the recording in
   `src/ragcourt/demo/` was made (`recording.json` has its date and command), record it again with real
   models, as design §13.1 says.
   For the first release on PyPI: the install lines in `README.md` and
   `tutorial/02-install-and-first-run.md` become `pip install ragcourt`, and their notes about PyPI go.
5. `verify-before-done` (with `real-model-tests` run, or the reason they were not), then `open-pr`
   (claude[bot] reviews it). The maintainer merges.
6. After the merge, on `main`: `git tag -a v<version> -m "ragcourt <version>"`. **Ask the maintainer
   before** `git push origin v<version>`: the tag runs `.github/workflows/release.yml`, which publishes
   to PyPI through trusted publishing (environment `pypi`). Watch it: `gh run watch`.
7. `gh release create v<version> --title "ragcourt <version>" --notes "<the CHANGELOG section>"`.
