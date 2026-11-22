import re

import ragdoctor


def test_version_is_semver() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", ragdoctor.__version__)


def test_errors_are_exported_and_typed() -> None:
    assert issubclass(ragdoctor.RagDoctorError, Exception)
    assert set(ragdoctor.__all__) >= {"RagDoctorError", "__version__"}
