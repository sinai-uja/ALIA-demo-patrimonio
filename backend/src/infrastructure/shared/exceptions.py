"""Infrastructure-layer exception hierarchy.

These exceptions wrap technical failures (network, external services,
parsing) so they can be translated into appropriate HTTP responses by the
API layer without leaking raw third-party errors.
"""


class InfrastructureError(Exception):
    """Base class for all infrastructure-level errors."""


class ExternalServiceUnavailableError(InfrastructureError):
    """Raised when an external dependency is unreachable or failing."""


class LLMUnavailableError(ExternalServiceUnavailableError):
    """Raised when the LLM provider is unavailable."""


class EmbeddingServiceUnavailableError(ExternalServiceUnavailableError):
    """Raised when the embedding service is unavailable."""


class RAGUnavailableError(ExternalServiceUnavailableError):
    """Raised when the RAG backend is unavailable."""


class LLMResponseParseError(InfrastructureError):
    """Raised when an LLM response cannot be parsed into the expected shape."""
