"""
Diagnostic script for Qwen3-Embedding-0.6B similarity search.

Checks score distributions, tests instruction prefixes, and sweeps thresholds
to identify why similarity search returns 0 results.

Usage:
    cd backend && uv run python scripts/embedding_diagnostics.py
"""

import asyncio
import sys

import asyncpg
import httpx
import numpy as np

# ---------- Config ----------
DB_DSN = "postgresql://uja:uja@localhost:15432/uja_iaph"
EMBEDDING_URL = "http://localhost:18001"
TABLE = "document_chunks_v4"
TOP_K = 40

TEST_QUERIES = [
    "cuevas del sacromonte",
    "alhambra granada",
    "iglesia barroca sevilla",
    "cerámica andaluza",
    "patrimonio inmueble jaén",
    "mezquita córdoba",
    "flamenco tradición andaluza",
    "castillo medieval cádiz",
]

INSTRUCTION_MODES = {
    "raw": lambda q: q,
    "instruct_heritage": lambda q: (
        "Instruct: Given a web search query, retrieve relevant passages "
        "about Spanish cultural heritage.\nQuery: " + q
    ),
    "instruct_short": lambda q: (
        "Instruct: Retrieve relevant heritage documents.\nQuery: " + q
    ),
    "instruct_generic": lambda q: (
        "Instruct: Given a web search query, retrieve relevant passages.\nQuery: " + q
    ),
}

THRESHOLDS = [0.20, 0.25, 0.30, 0.35, 0.40, 0.50, 0.60, 0.70, 0.80, 1.00]


async def check_embedding_service():
    """Verify the embedding service is running and report config."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{EMBEDDING_URL}/health")
        resp.raise_for_status()
        info = resp.json()
    print("=== Embedding Service Health ===")
    for k, v in info.items():
        print(f"  {k}: {v}")
    print()
    return info


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Call the embedding service."""
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{EMBEDDING_URL}/embed",
            json={"texts": texts},
        )
        resp.raise_for_status()
        return resp.json()["embeddings"]


def format_embedding(vec: list[float]) -> str:
    """Format embedding as pgvector string."""
    return "[" + ",".join(f"{v:.8f}" for v in vec) + "]"


async def pgvector_search(
    conn: asyncpg.Connection,
    embedding: list[float],
    table: str = TABLE,
    top_k: int = TOP_K,
    extra_where: str = "",
) -> list[dict]:
    """Run a raw pgvector cosine distance query."""
    vec_str = format_embedding(embedding)
    sql = f"""
        SELECT id, document_id, title, heritage_type, province,
               municipality, embedding <=> $1::vector AS score
        FROM {table}
        WHERE TRUE {extra_where}
        ORDER BY score ASC
        LIMIT $2
    """
    rows = await conn.fetch(sql, vec_str, top_k)
    return [dict(r) for r in rows]


def print_score_stats(scores: list[float], label: str):
    """Print percentile statistics for a list of scores."""
    arr = np.array(scores)
    print(f"  [{label}] n={len(arr)}")
    if len(arr) == 0:
        print("    (no results)")
        return
    pcts = [0, 10, 25, 50, 75, 90, 100]
    vals = np.percentile(arr, pcts)
    parts = [f"p{p}={v:.4f}" for p, v in zip(pcts, vals)]
    print(f"    {', '.join(parts)}")
    print(f"    mean={arr.mean():.4f}, std={arr.std():.4f}")


def print_top_results(results: list[dict], n: int = 10):
    """Print top-N results with title and score."""
    for i, r in enumerate(results[:n], 1):
        title = r["title"][:70] if r["title"] else "(no title)"
        print(
            f"    #{i:2d} score={r['score']:.4f} | {r['province']:12s} | {title}"
        )


async def run_diagnostics():
    print("Connecting to database...")
    conn = await asyncpg.connect(DB_DSN)

    try:
        # 1. Check table schema
        dim_row = await conn.fetchrow("""
            SELECT format_type(atttypid, atttypmod) AS col_type
            FROM pg_attribute
            WHERE attrelid = $1::regclass AND attname = 'embedding'
        """, TABLE)
        print(f"=== Table Schema: {TABLE} ===")
        print(f"  embedding column: {dim_row['col_type']}")
        count = await conn.fetchval(f"SELECT count(*) FROM {TABLE}")
        print(f"  total rows: {count:,}")
        print()

        # 2. Check embedding service
        await check_embedding_service()

        # 3. For each test query, test all instruction modes
        for query in TEST_QUERIES:
            print(f"{'='*80}")
            print(f"QUERY: \"{query}\"")
            print(f"{'='*80}")

            for mode_name, mode_fn in INSTRUCTION_MODES.items():
                wrapped = mode_fn(query)
                embeddings = await embed_texts([wrapped])
                vec = embeddings[0]

                results = await pgvector_search(conn, vec)
                scores = [r["score"] for r in results]

                print(f"\n  Mode: {mode_name}")
                if mode_name != "raw":
                    print(f"  Input: {wrapped[:100]}...")
                print_score_stats(scores, mode_name)
                print("  Top-10 results:")
                print_top_results(results)

                # Threshold sweep
                threshold_counts = {}
                for t in THRESHOLDS:
                    threshold_counts[t] = sum(1 for s in scores if s <= t)
                parts = [f"<={t:.2f}:{c}" for t, c in threshold_counts.items()]
                print(f"  Threshold sweep: {', '.join(parts)}")

            print()

        # 4. Global score distribution sample
        print(f"\n{'='*80}")
        print("GLOBAL SCORE DISTRIBUTION (random sample)")
        print(f"{'='*80}")

        # Embed a generic heritage query and check score distribution across all data
        generic_query = "patrimonio cultural andalucía"
        for mode_name in ["raw", "instruct_heritage"]:
            wrapped = INSTRUCTION_MODES[mode_name](generic_query)
            embeddings = await embed_texts([wrapped])
            vec = embeddings[0]

            # Get 200 nearest neighbors to see the full distribution
            results = await pgvector_search(conn, vec, top_k=200)
            scores = [r["score"] for r in results]
            print_score_stats(scores, f"generic_query_{mode_name}")

    finally:
        await conn.close()


async def main():
    try:
        await run_diagnostics()
    except httpx.ConnectError:
        print("ERROR: Cannot connect to embedding service at", EMBEDDING_URL)
        print("Make sure it's running: make infra")
        sys.exit(1)
    except asyncpg.PostgresError as e:
        print(f"ERROR: Database error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
