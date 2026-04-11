from __future__ import annotations

import logging
import time

from src.application.rag.dto.rag_dto import RAGQueryDTO, RAGResponseDTO, SourceDTO
from src.config import settings
from src.domain.rag.ports.llm_port import LLMPort
from src.domain.rag.ports.text_search_port import TextSearchPort
from src.domain.rag.ports.vector_search_port import VectorSearchPort
from src.domain.rag.prompts import SYSTEM_PROMPT, build_user_prompt
from src.domain.rag.services.context_assembly_service import ContextAssemblyService
from src.domain.rag.services.hybrid_search_service import HybridSearchService
from src.domain.rag.services.query_instruction_service import wrap_query_for_embedding
from src.domain.rag.services.relevance_filter_service import RelevanceFilterService
from src.domain.rag.services.reranking_service import RerankingService
from src.domain.shared.ports.embedding_port import EmbeddingPort

logger = logging.getLogger("iaph.rag.query")

ABSTENTION_ANSWER = (
    "No he encontrado informacion suficientemente relevante en la base de datos del IAPH "
    "para responder a tu pregunta. Por favor, reformula tu consulta o proporciona mas detalles."
)


class RAGQueryUseCase:
    """Orchestrates the full RAG pipeline: embed -> hybrid search -> filter -> assemble -> generate.

    """

    def __init__(
        self,
        embedding_port: EmbeddingPort,
        vector_search_port: VectorSearchPort,
        text_search_port: TextSearchPort,
        llm_port: LLMPort,
        context_assembly_service: ContextAssemblyService,
        relevance_filter_service: RelevanceFilterService,
        hybrid_search_service: HybridSearchService,
        reranking_service: RerankingService,
        retrieval_k: int = 20,
        similarity_only: bool = False,
        similarity_threshold: float = 0.25,
        reranker_enabled: bool = False,
    ) -> None:
        self._embedding_port = embedding_port
        self._vector_search_port = vector_search_port
        self._text_search_port = text_search_port
        self._llm_port = llm_port
        self._context_assembly_service = context_assembly_service
        self._relevance_filter_service = relevance_filter_service
        self._hybrid_search_service = hybrid_search_service
        self._reranking_service = reranking_service
        self._retrieval_k = retrieval_k
        self._similarity_only = similarity_only
        self._reranker_enabled = reranker_enabled
        self._similarity_filter = RelevanceFilterService(
            score_threshold=similarity_threshold,
        )

    async def execute(self, dto: RAGQueryDTO) -> RAGResponseDTO:
        t0 = time.perf_counter()
        logger.info("RAG pipeline start: query=%s", dto.query[:80])

        # 1. Embed the user query (with instruction prefix for Qwen3)
        # Normalize to lowercase for consistent embedding/reranking regardless of casing
        search_query = dto.query.lower()
        query_text = wrap_query_for_embedding(search_query, settings.embedding_query_instruction)
        t_embed = time.perf_counter()
        embeddings = await self._embedding_port.embed([query_text])
        embed_ms = (time.perf_counter() - t_embed) * 1000
        query_embedding = embeddings[0]
        logger.info(
            "Query embedded: %d chars → %d-dim vector", len(dto.query), len(query_embedding),
        )

        # Helper to return an abstention response
        def _abstain_response() -> RAGResponseDTO:
            return RAGResponseDTO(
                answer=ABSTENTION_ANSWER, sources=[], query=dto.query, abstained=True,
            )

        # 2. Retrieve chunks — pure similarity or full hybrid pipeline
        t_vsearch = time.perf_counter()
        vector_chunks = await self._vector_search_port.search(
            query_embedding=query_embedding,
            top_k=self._retrieval_k,
            heritage_type=dto.heritage_type_filter,
            province=dto.province_filter,
            municipality=dto.municipality_filter,
        )
        vsearch_ms = (time.perf_counter() - t_vsearch) * 1000

        # Track text search and reranker timing (set defaults for similarity-only)
        tsearch_ms: float = 0.0
        text_chunks: list = []
        rerank_ms: float = 0.0

        if self._similarity_only:
            # Pure similarity: vector search only, no fusion or reranking
            filtered_chunks = self._similarity_filter.filter(vector_chunks)
            logger.info(
                "Search results (similarity-only): vector=%d, filtered=%d, threshold=%.3f",
                len(vector_chunks), len(filtered_chunks),
                self._similarity_filter._score_threshold,
            )
            if not filtered_chunks:
                logger.info("Abstaining: no chunks passed similarity threshold")
                return _abstain_response()
            if self._reranker_enabled:
                # Neural reranking on similarity-only candidates
                t_rerank = time.perf_counter()
                final_chunks = await self._reranking_service.rerank(
                    query=search_query, chunks=filtered_chunks, top_k=dto.top_k,
                )
                rerank_ms = (time.perf_counter() - t_rerank) * 1000
                if not final_chunks:
                    logger.info("Abstaining: neural reranker returned no results")
                    return _abstain_response()
            else:
                final_chunks = sorted(filtered_chunks, key=lambda c: c.score)[:dto.top_k]
            for i, chunk in enumerate(final_chunks, 1):
                logger.info(
                    "Similarity #%d: score=%.4f | title: %s | type: %s | province: %s",
                    i, chunk.score, chunk.title[:60], chunk.heritage_type, chunk.province,
                )
        else:
            # Full hybrid pipeline: text search + RRF fusion + reranking
            t_tsearch = time.perf_counter()
            text_chunks = await self._text_search_port.search(
                query=search_query,
                top_k=self._retrieval_k,
                heritage_type=dto.heritage_type_filter,
                province=dto.province_filter,
                municipality=dto.municipality_filter,
            )
            tsearch_ms = (time.perf_counter() - t_tsearch) * 1000

            fused_chunks = self._hybrid_search_service.fuse(
                vector_results=vector_chunks,
                text_results=text_chunks,
                top_k=self._retrieval_k,
            )
            filtered_chunks = self._relevance_filter_service.filter(fused_chunks)
            logger.info(
                "Search results: vector=%d, fts=%d, fused=%d, filtered=%d",
                len(vector_chunks), len(text_chunks), len(fused_chunks), len(filtered_chunks),
            )
            if not filtered_chunks:
                logger.info("Abstaining: no chunks passed relevance threshold")
                return _abstain_response()

            if self._reranker_enabled:
                t_rerank = time.perf_counter()
                final_chunks = await self._reranking_service.rerank(
                    query=search_query, chunks=filtered_chunks, top_k=dto.top_k,
                )
                rerank_ms = (time.perf_counter() - t_rerank) * 1000
            else:
                t_rerank = time.perf_counter()
                final_chunks = self._reranking_service.rerank(
                    query=search_query, chunks=filtered_chunks, top_k=dto.top_k,
                )
                rerank_ms = (time.perf_counter() - t_rerank) * 1000
            if not final_chunks:
                logger.info("Abstaining: all chunks discarded by lexical filter")
                return _abstain_response()

        # 7. Assemble context from retrieved chunks
        context = self._context_assembly_service.assemble(final_chunks)

        # 8. Build prompts
        user_prompt = build_user_prompt(dto.query, context)

        logger.info(
            "Context assembled: %d final chunks, %d context chars, %d prompt chars",
            len(final_chunks), len(context), len(user_prompt),
        )

        # 9. Generate answer via LLM
        t_llm = time.perf_counter()
        answer = await self._llm_port.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            context_chunks=final_chunks,
        )
        llm_ms = (time.perf_counter() - t_llm) * 1000

        # 10. Map to response DTO
        sources = [
            SourceDTO(
                title=chunk.title,
                url=chunk.url,
                score=chunk.score,
                heritage_type=chunk.heritage_type,
                province=chunk.province,
                municipality=chunk.municipality,
                document_id=chunk.document_id,
                content=chunk.content,
                metadata=chunk.metadata,
            )
            for chunk in final_chunks
        ]

        logger.info(
            "RAG pipeline complete: %d chars answer, %d sources",
            len(answer), len(sources),
        )
        logger.debug("RAG LLM answer:\n%s", answer)

        elapsed_ms = (time.perf_counter() - t0) * 1000

        # Build pipeline_steps for traceability
        try:
            filter_parts = []
            if dto.heritage_type_filter:
                filter_parts.append(f"type={dto.heritage_type_filter}")
            if dto.province_filter:
                filter_parts.append(f"province={dto.province_filter}")
            if dto.municipality_filter:
                filter_parts.append(f"municipality={dto.municipality_filter}")
            filter_str = ", ".join(filter_parts) if filter_parts else "none"

            pipeline_steps: list[dict] = [
                {
                    "step": "embedding",
                    "input": {"text": dto.query[:80], "chars": len(dto.query)},
                    "output": {"dim": len(query_embedding)},
                    "elapsed_ms": round(embed_ms, 1),
                },
                {
                    "step": "vector_search",
                    "input": {"top_k": self._retrieval_k, "filters": filter_str},
                    "output": {
                        "count": len(vector_chunks),
                        "top_score": round(vector_chunks[0].score, 4) if vector_chunks else None,
                    },
                    "results": [
                        {
                            "rank": i, "score": round(c.score, 4),
                            "title": c.title[:60], "type": c.heritage_type,
                            "document_id": c.document_id,
                        }
                        for i, c in enumerate(vector_chunks[:15], 1)
                    ],
                    "elapsed_ms": round(vsearch_ms, 1),
                },
            ]

            if not self._similarity_only and text_chunks:
                pipeline_steps.append({
                    "step": "text_search",
                    "input": {"query": search_query[:80], "top_k": self._retrieval_k},
                    "output": {"count": len(text_chunks)},
                    "elapsed_ms": round(tsearch_ms, 1),
                })
                pipeline_steps.append({
                    "step": "fusion",
                    "input": {"vector_count": len(vector_chunks), "text_count": len(text_chunks)},
                    "output": {"fused_count": len(filtered_chunks)},
                })

            if self._reranker_enabled:
                pipeline_steps.append({
                    "step": "reranker",
                    "input": {"candidates": len(filtered_chunks), "top_k": dto.top_k},
                    "output": {
                        "count": len(final_chunks),
                        "top_score": round(final_chunks[0].score, 4) if final_chunks else None,
                    },
                    "results": [
                        {
                            "rank": i, "score": round(c.score, 4),
                            "title": c.title[:60], "type": c.heritage_type,
                            "document_id": c.document_id,
                        }
                        for i, c in enumerate(final_chunks[:15], 1)
                    ],
                    "elapsed_ms": round(rerank_ms, 1),
                })

            pipeline_steps.append({
                "step": "llm_generate",
                "input": {"context_chunks": len(final_chunks), "prompt_chars": len(user_prompt)},
                "output": {"answer_chars": len(answer)},
                "elapsed_ms": round(llm_ms, 1),
            })
        except Exception:
            logger.warning("Failed to build RAG pipeline_steps", exc_info=True)
            pipeline_steps = []

        return RAGResponseDTO(
            answer=answer,
            sources=sources,
            query=dto.query,
            pipeline_steps=pipeline_steps,
        )
