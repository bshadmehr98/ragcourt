import re

import ragcourt


def test_version_is_semver() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", ragcourt.__version__)


def test_errors_are_exported_and_typed() -> None:
    assert issubclass(ragcourt.RagCourtError, Exception)
    assert set(ragcourt.__all__) >= {"RagCourtError", "__version__"}
