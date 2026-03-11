from dataclasses import dataclass


@dataclass
class IngestDocumentsCommand:
    """Command to trigger document ingestion from a parquet source."""

    source_path: str
    heritage_type: str
    chunk_size: int = 512
    chunk_overlap: int = 64


@dataclass
class IngestResultDTO:
    """Result of a document ingestion run."""

    total_documents: int
    total_chunks: int
    skipped_chunks: int
