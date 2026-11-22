"""ragcourt: rank RAG stages on your own documents and say which stage caused each miss.

The design is in design/current.md; its §17 says what is built. The public API is listed in ``__all__``
and grows as the milestone's steps land. Your own stages are registered with the decorators of
``ragcourt.stages``.
"""

from ragcourt.errors import (
    BudgetExceeded,
    ChunkNotInSource,
    ConfigError,
    EndpointError,
    ExtraMissing,
    FormatVersionError,
    GeneratedCodeRejected,
    RagCourtError,
)
from ragcourt.types import Corpus, Document, Skipped

__version__ = "0.1.0"

__all__ = [
    "BudgetExceeded",
    "ChunkNotInSource",
    "ConfigError",
    "Corpus",
    "Document",
    "EndpointError",
    "ExtraMissing",
    "FormatVersionError",
    "GeneratedCodeRejected",
    "RagCourtError",
    "Skipped",
    "__version__",
]
