import re
import uuid

from src.domain.documents.entities.chunk import Chunk
from src.domain.documents.entities.document import Document
from src.domain.documents.exceptions import InvalidChunkingConfigurationError


class ChunkingService:
    """Splits document text into overlapping chunks using paragraph-aware splitting.

    Splits on paragraph boundaries (double newline) first, then groups paragraphs
    into chunks of at most `chunk_size` words. Never cuts mid-paragraph unless a
    single paragraph exceeds the chunk size (fallback: word-level split).
    """

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64) -> None:
        if chunk_overlap >= chunk_size:
            raise InvalidChunkingConfigurationError(
                "chunk_overlap must be less than chunk_size"
            )
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(self, document: Document) -> list[Chunk]:
        paragraphs = self._split_paragraphs(document.text)
        if not paragraphs:
            return []

        chunks: list[Chunk] = []
        current_paragraphs: list[str] = []
        current_word_count = 0
        chunk_index = 0

        for para in paragraphs:
            para_words = len(para.split())

            # Single paragraph exceeds chunk size: split it by words
            if para_words > self.chunk_size:
                # Flush current buffer first
                if current_paragraphs:
                    chunks.append(self._make_chunk(
                        document, current_paragraphs, chunk_index
                    ))
                    chunk_index += 1
                    current_paragraphs = []
                    current_word_count = 0

                # Word-level fallback for oversized paragraph
                words = para.split()
                step = self.chunk_size - self.chunk_overlap
                start = 0
                while start < len(words):
                    end = min(start + self.chunk_size, len(words))
                    chunk_text = " ".join(words[start:end])
                    chunks.append(Chunk(
                        id=uuid.uuid4(),
                        document_id=document.id,
                        content=chunk_text,
                        chunk_index=chunk_index,
                        token_count=end - start,
                    ))
                    chunk_index += 1
                    start += step
                    if start < len(words) and len(words) - start <= self.chunk_overlap:
                        break
                continue

            # Adding this paragraph would exceed the limit: flush
            if current_word_count + para_words > self.chunk_size and current_paragraphs:
                chunks.append(self._make_chunk(
                    document, current_paragraphs, chunk_index
                ))
                chunk_index += 1

                # Overlap: keep last paragraph(s) up to chunk_overlap words
                overlap_paragraphs: list[str] = []
                overlap_words = 0
                for p in reversed(current_paragraphs):
                    pw = len(p.split())
                    if overlap_words + pw > self.chunk_overlap:
                        break
                    overlap_paragraphs.insert(0, p)
                    overlap_words += pw

                current_paragraphs = overlap_paragraphs
                current_word_count = overlap_words

            current_paragraphs.append(para)
            current_word_count += para_words

        # Flush remaining
        if current_paragraphs:
            chunks.append(self._make_chunk(
                document, current_paragraphs, chunk_index
            ))

        return chunks

    @staticmethod
    def _split_paragraphs(text: str) -> list[str]:
        """Split text on double newlines, filtering empty paragraphs."""
        parts = re.split(r"\n\s*\n", text.strip())
        return [p.strip() for p in parts if p.strip()]

    @staticmethod
    def _make_chunk(
        document: Document, paragraphs: list[str], chunk_index: int
    ) -> Chunk:
        content = "\n\n".join(paragraphs)
        token_count = len(content.split())
        return Chunk(
            id=uuid.uuid4(),
            document_id=document.id,
            content=content,
            chunk_index=chunk_index,
            token_count=token_count,
        )
