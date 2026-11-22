"""ragdoctor: rank RAG stages on your own documents and say which stage caused each miss.

The design is in design/current.md (design 0001 is proposed). Nothing of it is built yet; the public API
will be listed here with an explicit ``__all__`` as it is built.
"""

from ragdoctor.errors import RagDoctorError

__version__ = "0.1.0"

__all__ = [
    "RagDoctorError",
    "__version__",
]
