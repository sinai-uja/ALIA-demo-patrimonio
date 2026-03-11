import uuid

from src.domain.documents.entities.chunk import Chunk
from src.domain.documents.entities.document import Document


class ChunkingService:
    """Splits document text into overlapping chunks using word-boundary splitting.

    Uses word count as a proxy for token count: splits on whitespace, then groups
    words into chunks of at most `chunk_size` words with `chunk_overlap` word overlap.
    """

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(self, document: Document) -> list[Chunk]:
        words = document.text.split()
        if not words:
            return []

        chunks: list[Chunk] = []
        step = self.chunk_size - self.chunk_overlap
        start = 0
        chunk_index = 0

        while start < len(words):
            end = min(start + self.chunk_size, len(words))
            chunk_words = words[start:end]
            content = " ".join(chunk_words)
            token_count = len(chunk_words)

            chunks.append(
                Chunk(
                    id=uuid.uuid4(),
                    document_id=document.id,
                    content=content,
                    chunk_index=chunk_index,
                    token_count=token_count,
                )
            )

            chunk_index += 1
            start += step

            # Avoid creating a tiny trailing chunk that duplicates the previous one
            if start < len(words) and len(words) - start <= self.chunk_overlap:
                break

        return chunks
