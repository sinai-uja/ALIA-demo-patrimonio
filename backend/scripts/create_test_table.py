"""
Create an isolated test table with different embedding variants to compare
enriched vs clean document content for Qwen3-Embedding-0.6B.

Usage:
    cd backend && uv run python scripts/create_test_table.py
"""

import asyncio
import re
import sys
import time

import asyncpg
import httpx

# ---------- Config ----------
DB_DSN = "postgresql://uja:uja@localhost:15432/uja_iaph"
EMBEDDING_URL = "http://localhost:18001"
SOURCE_TABLE = "document_chunks_v4"
TEST_TABLE = "document_chunks_test"
BATCH_SIZE = 8  # texts per embedding request
SOURCE_LIMIT = 500  # chunks to select from source table

# Regex patterns to strip enrichment prefixes from v4 natural-language templates
ENRICHMENT_PATTERNS = [
    # v4 natural language templates
    r"^Bien inmueble titulado\s+'[^']*'\.\s*",
    r"^Bien mueble titulado\s+'[^']*'\.\s*",
    r"^Patrimonio inmaterial titulado\s+'[^']*'\.\s*",
    r"^Paisaje cultural titulado\s+'[^']*'\.\s*",
    # Common metadata lines that follow the title
    r"Es una propiedad de naturaleza[^.]*\.\s*",
    r"Ubicado en el municipio de[^.]*\.\s*",
    r"De estilo[^.]*\.\s*",
    r"Pertenece al período[^.]*\.\s*",
    r"De los materiales[^.]*\.\s*",
    r"De técnica[^.]*\.\s*",
    # v2/v3 header format
    r"^Titulo:[^\n]*\n---\n",
]


def strip_enrichment(content: str) -> str:
    """Remove metadata enrichment from chunk content, keeping only raw text."""
    cleaned = content
    for pattern in ENRICHMENT_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Call the embedding service."""
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{EMBEDDING_URL}/embed",
            json={"texts": texts},
        )
        resp.raise_for_status()
        return resp.json()["embeddings"]


async def embed_in_batches(texts: list[str], batch_size: int = BATCH_SIZE) -> list[list[float]]:
    """Embed texts in batches to avoid memory issues."""
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        embeddings = await embed_texts(batch)
        all_embeddings.extend(embeddings)
        if (i // batch_size) % 10 == 0:
            print(f"  Embedded {len(all_embeddings)}/{len(texts)} texts...")
    return all_embeddings


def format_embedding(vec: list[float]) -> str:
    return "[" + ",".join(f"{v:.8f}" for v in vec) + "]"


async def main():
    print("Connecting to database...")
    conn = await asyncpg.connect(DB_DSN)

    try:
        # 1. Drop and recreate test table
        print(f"\n=== Creating test table: {TEST_TABLE} ===")
        await conn.execute(f"DROP TABLE IF EXISTS {TEST_TABLE}")
        await conn.execute(f"""
            CREATE TABLE {TEST_TABLE} (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                document_id VARCHAR NOT NULL,
                heritage_type VARCHAR NOT NULL,
                title VARCHAR NOT NULL,
                province VARCHAR NOT NULL,
                municipality VARCHAR,
                url VARCHAR NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                original_content TEXT,
                clean_content TEXT,
                token_count INTEGER DEFAULT 0,
                embedding vector(1024),
                variant VARCHAR(32) NOT NULL,
                metadata JSONB DEFAULT '{{}}'::jsonb,
                created_at TIMESTAMPTZ DEFAULT now()
            )
        """)
        print("  Table created.")

        # 2. Select source chunks (diverse set across provinces)
        print(f"\n=== Selecting source chunks from {SOURCE_TABLE} ===")
        source_rows = await conn.fetch(f"""
            SELECT id, document_id, heritage_type, title, province,
                   municipality, url, chunk_index, content, token_count, metadata
            FROM {SOURCE_TABLE}
            WHERE province IN ('Granada', 'Sevilla', 'Córdoba', 'Jaén', 'Cádiz')
            ORDER BY random()
            LIMIT $1
        """, SOURCE_LIMIT)
        print(f"  Selected {len(source_rows)} source chunks")

        # 3. Prepare texts for each variant
        original_texts = [r["content"] for r in source_rows]
        clean_texts = [strip_enrichment(r["content"]) for r in source_rows]

        # Show a few examples of enrichment stripping
        print("\n=== Enrichment stripping examples ===")
        for i in range(min(3, len(source_rows))):
            orig = original_texts[i][:150]
            clean = clean_texts[i][:150]
            print(f"  [{i}] Original: {orig}...")
            print(f"  [{i}] Cleaned:  {clean}...")
            print()

        # 4. Embed each variant
        print("=== Embedding variant: baseline (enriched content as-is) ===")
        t0 = time.time()
        baseline_embeddings = await embed_in_batches(original_texts)
        print(f"  Done in {time.time()-t0:.1f}s")

        print("=== Embedding variant: clean (stripped content) ===")
        t0 = time.time()
        clean_embeddings = await embed_in_batches(clean_texts)
        print(f"  Done in {time.time()-t0:.1f}s")

        # 5. Insert rows
        print(f"\n=== Inserting into {TEST_TABLE} ===")
        insert_sql = f"""
            INSERT INTO {TEST_TABLE}
            (document_id, heritage_type, title, province, municipality, url,
             chunk_index, content, original_content, clean_content, token_count,
             embedding, variant, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
        """

        count = 0
        for i, row in enumerate(source_rows):
            # Baseline variant
            await conn.execute(
                insert_sql,
                row["document_id"], row["heritage_type"], row["title"],
                row["province"], row["municipality"], row["url"],
                row["chunk_index"], original_texts[i], original_texts[i],
                clean_texts[i], row["token_count"],
                format_embedding(baseline_embeddings[i]),
                "baseline", row["metadata"],
            )
            # Clean variant
            await conn.execute(
                insert_sql,
                row["document_id"], row["heritage_type"], row["title"],
                row["province"], row["municipality"], row["url"],
                row["chunk_index"], clean_texts[i], original_texts[i],
                clean_texts[i], row["token_count"],
                format_embedding(clean_embeddings[i]),
                "clean", row["metadata"],
            )
            count += 2

        print(f"  Inserted {count} rows ({count//2} per variant)")

        # 6. Create HNSW index
        print("\n=== Creating HNSW index ===")
        await conn.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_{TEST_TABLE}_embedding_hnsw
            ON {TEST_TABLE}
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
        """)
        print("  Index created.")

        # 7. Summary
        total = await conn.fetchval(f"SELECT count(*) FROM {TEST_TABLE}")
        variants = await conn.fetch(f"""
            SELECT variant, count(*) as cnt
            FROM {TEST_TABLE}
            GROUP BY variant
            ORDER BY variant
        """)
        print("\n=== Summary ===")
        print(f"  Total rows: {total}")
        for v in variants:
            print(f"  Variant '{v['variant']}': {v['cnt']} rows")

    finally:
        await conn.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except httpx.ConnectError:
        print("ERROR: Cannot connect to embedding service at", EMBEDDING_URL)
        sys.exit(1)
    except asyncpg.PostgresError as e:
        print(f"ERROR: Database error: {e}")
        sys.exit(1)
