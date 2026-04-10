"""Documents domain exceptions."""


class DomainError(Exception):
    """Base class for domain-level errors in the documents context."""


class InvalidChunkingConfigurationError(DomainError):
    """Raised when a ChunkingService is configured with incoherent parameters."""
