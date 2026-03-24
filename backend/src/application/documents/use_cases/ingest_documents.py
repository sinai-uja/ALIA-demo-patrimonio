import asyncio
import logging

from src.application.documents.dto.ingest_dto import IngestDocumentsCommand, IngestResultDTO
from src.domain.documents.entities.chunk_embedding import ChunkEmbedding
from src.domain.documents.ports.document_loader import DocumentLoader
from src.domain.documents.ports.document_repository import DocumentRepository
from src.domain.documents.ports.embedding_port import EmbeddingPort
from src.domain.documents.services.chunking_service import ChunkingService
from src.domain.documents.value_objects.heritage_type import HeritageType

logger = logging.getLogger("iaph")

EMBEDDING_BATCH_SIZE = 2

# Type-specific metadata fields to prepend to chunk content for richer embeddings (v2/v3).
# Each entry is (parquet_column_name, human_readable_label).
_ENRICHMENT_FIELDS: dict[HeritageType, list[tuple[str, str]]] = {
    HeritageType.PATRIMONIO_MUEBLE: [
        ("authors", "Autor"),
        ("styles", "Estilo"),
        ("historic_periods", "Periodo"),
        ("chronology", "Cronologia"),
        ("materials", "Material"),
        ("techniques", "Tecnica"),
        ("type", "Tipo bien"),
        ("protection", "Proteccion"),
        ("iconographies", "Iconografia"),
    ],
    HeritageType.PATRIMONIO_INMUEBLE: [
        ("characterisation", "Caracterizacion"),
        ("protection", "Proteccion"),
    ],
    HeritageType.PATRIMONIO_INMATERIAL: [
        ("activity_types", "Tipo actividad"),
        ("subject_topic", "Tema"),
    ],
    HeritageType.PAISAJE_CULTURAL: [
        ("topic", "Tema"),
        ("landscape_demarcation", "Demarcacion"),
    ],
}


class IngestDocumentsUseCase:
    """Orchestrates the full document ingestion pipeline:
    load -> chunk -> skip duplicates -> embed -> persist.
    """

    def __init__(
        self,
        document_loader: DocumentLoader,
        chunking_service: ChunkingService,
        embedding_port: EmbeddingPort,
        document_repository: DocumentRepository,
        chunks_version: str = "v1",
    ) -> None:
        self._loader = document_loader
        self._chunker = chunking_service
        self._embedding_port = embedding_port
        self._repository = document_repository
        self._chunks_version = chunks_version

    async def execute(self, command: IngestDocumentsCommand) -> IngestResultDTO:
        heritage_type = HeritageType(command.heritage_type)

        # Reconfigure chunker with command parameters
        self._chunker.chunk_size = command.chunk_size
        self._chunker.chunk_overlap = command.chunk_overlap

        total_documents = 0
        total_chunks = 0
        skipped_chunks = 0

        for document in self._loader.load_documents(command.source_path, heritage_type):
            total_documents += 1
            chunks = self._chunker.chunk_document(document)

            # Filter out already-existing chunks (idempotent ingestion)
            new_chunks = []
            for chunk in chunks:
                exists = await self._repository.chunk_exists(
                    chunk.document_id, chunk.chunk_index
                )
                if exists:
                    skipped_chunks += 1
                else:
                    new_chunks.append(chunk)

            # Embed and persist in batches
            # Prepend metadata to each chunk for richer embeddings
            for batch_start in range(0, len(new_chunks), EMBEDDING_BATCH_SIZE):
                batch = new_chunks[batch_start : batch_start + EMBEDDING_BATCH_SIZE]
                texts = [
                    self._enrich_for_embedding(document, c.content) for c in batch
                ]

                embeddings = await self._embed_with_retry(texts)

                for chunk, embedding_vector in zip(batch, embeddings):
                    embedding = ChunkEmbedding(
                        chunk_id=chunk.id,
                        embedding=embedding_vector,
                    )
                    await self._repository.save_chunk_with_embedding(
                        document, chunk, embedding
                    )

            total_chunks += len(new_chunks)
            await self._repository.commit()

            if total_documents % 50 == 0:
                logger.info(
                    "Ingestion progress: %d documents processed, %d chunks created",
                    total_documents,
                    total_chunks,
                )

        logger.info(
            "Ingestion complete: %d documents, %d new chunks, %d skipped",
            total_documents,
            total_chunks,
            skipped_chunks,
        )

        return IngestResultDTO(
            total_documents=total_documents,
            total_chunks=total_chunks,
            skipped_chunks=skipped_chunks,
        )

    async def _embed_with_retry(self, texts: list[str]) -> list[list[float]]:
        """Embed texts with fallback to one-by-one on OOM errors."""
        try:
            return await self._embedding_port.embed(texts)
        except Exception:
            if len(texts) <= 1:
                raise
            logger.warning(
                "Embedding batch of %d failed, retrying one-by-one", len(texts)
            )
            await asyncio.sleep(2)
            results = []
            for t in texts:
                result = await self._embedding_port.embed([t])
                results.append(result[0])
            return results

    def _enrich_for_embedding(self, document, content: str) -> str:
        """Prepend document metadata to chunk content for richer embeddings.

        For v4, uses natural language templates per heritage type.
        For v1/v2/v3, uses pipe-separated key-value header.
        """
        if self._chunks_version == "v4":
            return self._enrich_v4(document, content)
        return self._enrich_header(document, content)

    @staticmethod
    def _enrich_header(document, content: str) -> str:
        """v2/v3 enrichment: pipe-separated metadata header."""
        parts = [f"Titulo: {document.title}"]
        parts.append(f"Tipo: {document.heritage_type.value}")
        parts.append(f"Provincia: {document.province}")
        if document.municipality:
            parts.append(f"Municipio: {document.municipality}")

        # Type-specific enrichment from parquet metadata
        for field_key, label in _ENRICHMENT_FIELDS.get(document.heritage_type, []):
            value = document.metadata.get(field_key)
            if value is not None and str(value).strip() and str(value).lower() != "nan":
                parts.append(f"{label}: {value}")

        header = " | ".join(parts)
        return f"{header}\n---\n{content}"

    @staticmethod
    def _get_meta(document, key: str) -> str | None:
        """Get a metadata value, returning None if missing or empty."""
        value = document.metadata.get(key)
        if value is None or str(value).strip() == "" or str(value).lower() == "nan":
            return None
        return str(value).strip()

    def _enrich_v4(self, document, content: str) -> str:
        """v4 enrichment: natural language templates per heritage type."""
        ht = document.heritage_type
        if ht == HeritageType.PAISAJE_CULTURAL:
            return self._template_paisaje(document, content)
        if ht == HeritageType.PATRIMONIO_INMATERIAL:
            return self._template_inmaterial(document, content)
        if ht == HeritageType.PATRIMONIO_INMUEBLE:
            return self._template_inmueble(document, content)
        if ht == HeritageType.PATRIMONIO_MUEBLE:
            return self._template_mueble(document, content)
        # Fallback to header-based enrichment for unknown types
        return self._enrich_header(document, content)

    def _template_paisaje(self, document, content: str) -> str:
        header = (
            f"Paisaje cultural titulado '{document.title}' "
            f"y ubicado en la provincia de '{document.province}'."
        )
        return f"{header}\n{content}"

    def _template_inmaterial(self, document, content: str) -> str:
        activity_types = self._get_meta(document, "activity_types")
        subject_topic = self._get_meta(document, "subject_topic")
        district = self._get_meta(document, "district")
        municipality = document.municipality
        province = document.province

        parts = [f"Bien inmaterial titulado '{document.title}'"]
        if activity_types and subject_topic:
            parts[0] += f", clasificado como {activity_types} bajo la categoría {subject_topic}"
        elif activity_types:
            parts[0] += f", clasificado como {activity_types}"
        elif subject_topic:
            parts[0] += f", de categoría {subject_topic}"
        parts[0] += "."

        location_parts = [p for p in [district, municipality, province] if p]
        if location_parts:
            parts.append(f"Ubicado en {', '.join(location_parts)}.")

        header = " ".join(parts)
        return f"{header}\n{content}"

    def _template_inmueble(self, document, content: str) -> str:
        characterisation = self._get_meta(document, "characterisation")
        type_val = self._get_meta(document, "type")
        municipality = document.municipality
        province = document.province
        style = self._get_meta(document, "styles")
        historic_periods = self._get_meta(document, "historic_periods")

        line1 = f"Bien inmueble titulado '{document.title}'."
        if characterisation and type_val:
            line1 = (
                f"Bien inmueble titulado '{document.title}'. "
                f"Es una propiedad de naturaleza {characterisation} y tipo {type_val}."
            )
        elif characterisation:
            line1 = (
                f"Bien inmueble titulado '{document.title}'. "
                f"Es una propiedad de naturaleza {characterisation}."
            )

        if municipality:
            line1 += f" Ubicado en el municipio de {municipality}, provincia de {province}."
        else:
            line1 += f" Ubicado en la provincia de {province}."

        lines = [line1]
        if style and historic_periods:
            lines.append(f"De estilo {style} y período histórico {historic_periods}.")
        elif style:
            lines.append(f"De estilo {style}.")
        elif historic_periods:
            lines.append(f"De período histórico {historic_periods}.")

        header = "\n".join(lines)
        return f"{header}\n{content}"

    def _template_mueble(self, document, content: str) -> str:
        type_val = self._get_meta(document, "type")
        municipality = document.municipality
        province = document.province
        style = self._get_meta(document, "styles")
        historic_periods = self._get_meta(document, "historic_periods")

        if type_val:
            line1 = f"Bien mueble titulado '{document.title}' de tipo {type_val}."
        else:
            line1 = f"Bien mueble titulado '{document.title}'."

        if municipality:
            line1 += f" Ubicado en el municipio de {municipality}, provincia de {province}."
        else:
            line1 += f" Ubicado en la provincia de {province}."

        lines = [line1]
        if style and historic_periods:
            lines.append(f"De estilo {style} y período histórico {historic_periods}.")
        elif style:
            lines.append(f"De estilo {style}.")
        elif historic_periods:
            lines.append(f"De período histórico {historic_periods}.")

        header = "\n".join(lines)
        return f"{header}\n{content}"
