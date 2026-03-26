"""
Benchmark retrieval quality across different configurations:
- Query instruction modes (raw vs instruct_short)
- Document variants (baseline enriched vs clean content)
- Different thresholds

Usage:
    cd backend && uv run python scripts/benchmark_retrieval.py --discover   # find ground truth
    cd backend && uv run python scripts/benchmark_retrieval.py              # run benchmarks
"""

import argparse
import asyncio
import csv
import os
import sys
from datetime import datetime

import asyncpg
import httpx
import numpy as np

# ---------- Config ----------
DB_DSN = "postgresql://uja:uja@localhost:15432/uja_iaph"
EMBEDDING_URL = "http://localhost:18001"
PROD_TABLE = "document_chunks_v4"
TEST_TABLE = "document_chunks_test"
TOP_K = 40
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")

INSTRUCTION_MODES = {
    "raw": lambda q: q,
    "instruct_short": lambda q: (
        "Instruct: Retrieve relevant heritage documents.\nQuery: " + q
    ),
    "instruct_heritage": lambda q: (
        "Instruct: Given a web search query, retrieve relevant passages "
        "about Spanish cultural heritage.\nQuery: " + q
    ),
}

THRESHOLDS = [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]

# Ground truth: query -> list of expected document titles (substring match)
# Populated after running --discover mode
GROUND_TRUTH = {
    "cuevas del sacromonte": [
        "Sector Valparaiso-Sacromonte",
        "Sacromonte",
        "Cueva",
        "Casas-cueva",
    ],
    "alhambra granada": [
        "Alhambra",
        "Vista de la Alhambra",
    ],
    "mezquita córdoba": [
        "Mezquita",
        "Centro Histórico de Córdoba",
    ],
    "iglesia barroca sevilla": [
        "Iglesia",
        "Retablo",
    ],
    "patrimonio inmueble jaén": [
        "Jaén",
        "Centro Histórico de Jaén",
    ],
    "cerámica andaluza": [
        "cerámica",
        "Cerámica",
    ],
    "castillo medieval cádiz": [
        "Castillo",
        "Cádiz",
    ],
    "flamenco tradición andaluza": [
        "Flamenco",
        "flamenco",
    ],
}


async def embed_texts(texts: list[str]) -> list[list[float]]:
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{EMBEDDING_URL}/embed", json={"texts": texts},
        )
        resp.raise_for_status()
        return resp.json()["embeddings"]


def format_embedding(vec: list[float]) -> str:
    return "[" + ",".join(f"{v:.8f}" for v in vec) + "]"


async def search(conn, table, embedding, top_k=TOP_K, variant=None):
    vec_str = format_embedding(embedding)
    variant_clause = f"AND variant = '{variant}'" if variant else ""
    sql = f"""
        SELECT document_id, title, heritage_type, province,
               embedding <=> $1::vector AS score
        FROM {table}
        WHERE TRUE {variant_clause}
        ORDER BY score ASC
        LIMIT $2
    """
    rows = await conn.fetch(sql, vec_str, top_k)
    return [dict(r) for r in rows]


def check_relevance(title: str, expected_patterns: list[str]) -> bool:
    """Check if a result title matches any expected pattern (substring)."""
    title_lower = title.lower()
    return any(p.lower() in title_lower for p in expected_patterns)


def compute_metrics(results: list[dict], expected_patterns: list[str], threshold: float):
    """Compute retrieval metrics for a set of results."""
    filtered = [r for r in results if r["score"] <= threshold]
    scores = [r["score"] for r in results[:20]]

    # Recall@k: fraction of results in top-k that are relevant
    relevant_at_5 = sum(1 for r in filtered[:5] if check_relevance(r["title"], expected_patterns))
    relevant_at_10 = sum(1 for r in filtered[:10] if check_relevance(r["title"], expected_patterns))
    relevant_at_20 = sum(1 for r in filtered[:20] if check_relevance(r["title"], expected_patterns))

    # MRR: reciprocal rank of first relevant result
    mrr = 0.0
    for i, r in enumerate(filtered, 1):
        if check_relevance(r["title"], expected_patterns):
            mrr = 1.0 / i
            break

    return {
        "n_filtered": len(filtered),
        "relevant@5": relevant_at_5,
        "relevant@10": relevant_at_10,
        "relevant@20": relevant_at_20,
        "mrr": mrr,
        "best_score": scores[0] if scores else None,
        "median_score": float(np.median(scores)) if scores else None,
    }


async def discover_mode(conn):
    """Print top results for each query to help build ground truth."""
    print("=== DISCOVERY MODE ===")
    print("Showing top-20 results per query with instruct_short mode.\n")

    for query in GROUND_TRUTH:
        wrapped = INSTRUCTION_MODES["instruct_short"](query)
        embeddings = await embed_texts([wrapped])

        # Search production table
        results = await search(conn, PROD_TABLE, embeddings[0], top_k=20)

        print(f'Query: "{query}"')
        print(f"{'#':>3} {'Score':>7} {'Province':>12} Title")
        print("-" * 90)
        for i, r in enumerate(results, 1):
            title = r["title"][:60]
            print(f"{i:3d} {r['score']:7.4f} {r['province']:>12s} {title}")
        print()

    # Also search test table if it exists
    test_exists = await conn.fetchval(
        "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = $1)",
        TEST_TABLE,
    )
    if test_exists:
        print("\n=== TEST TABLE RESULTS (clean variant) ===\n")
        for query in list(GROUND_TRUTH)[:3]:
            wrapped = INSTRUCTION_MODES["instruct_short"](query)
            embeddings = await embed_texts([wrapped])
            results = await search(conn, TEST_TABLE, embeddings[0], top_k=10, variant="clean")

            print(f'Query: "{query}" (clean variant)')
            for i, r in enumerate(results, 1):
                title = r["title"][:60]
                print(f"  {i:3d} {r['score']:7.4f} {r['province']:>12s} {title}")
            print()


async def benchmark_mode(conn):
    """Run full benchmarks across all configurations."""
    print("=== BENCHMARK MODE ===\n")

    all_results = []

    # Check if test table exists
    test_exists = await conn.fetchval(
        "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = $1)",
        TEST_TABLE,
    )

    # Build configurations
    configs = []
    for mode_name in ["raw", "instruct_short", "instruct_heritage"]:
        configs.append({"mode": mode_name, "table": PROD_TABLE, "variant": None, "label": f"prod_{mode_name}"})

    if test_exists:
        for mode_name in ["raw", "instruct_short"]:
            for variant in ["baseline", "clean"]:
                configs.append({
                    "mode": mode_name, "table": TEST_TABLE, "variant": variant,
                    "label": f"test_{variant}_{mode_name}",
                })

    for threshold in THRESHOLDS:
        print(f"\n--- Threshold: {threshold:.2f} ---")
        header = f"{'Config':<30} {'N':>4} {'R@5':>4} {'R@10':>5} {'R@20':>5} {'MRR':>6} {'Best':>7} {'Med':>7}"
        print(header)
        print("-" * len(header))

        for config in configs:
            query_metrics = []
            for query, patterns in GROUND_TRUTH.items():
                wrapped = INSTRUCTION_MODES[config["mode"]](query)
                embeddings = await embed_texts([wrapped])

                results = await search(
                    conn, config["table"], embeddings[0],
                    variant=config["variant"],
                )
                metrics = compute_metrics(results, patterns, threshold)
                query_metrics.append(metrics)

                all_results.append({
                    "config": config["label"],
                    "threshold": threshold,
                    "query": query,
                    **metrics,
                })

            # Aggregate across queries
            avg_n = np.mean([m["n_filtered"] for m in query_metrics])
            avg_r5 = np.mean([m["relevant@5"] for m in query_metrics])
            avg_r10 = np.mean([m["relevant@10"] for m in query_metrics])
            avg_r20 = np.mean([m["relevant@20"] for m in query_metrics])
            avg_mrr = np.mean([m["mrr"] for m in query_metrics])
            avg_best = np.mean([m["best_score"] for m in query_metrics if m["best_score"] is not None])
            avg_med = np.mean([m["median_score"] for m in query_metrics if m["median_score"] is not None])

            print(
                f"{config['label']:<30} {avg_n:4.0f} {avg_r5:4.1f} {avg_r10:5.1f} "
                f"{avg_r20:5.1f} {avg_mrr:6.3f} {avg_best:7.4f} {avg_med:7.4f}"
            )

    # Save detailed results to CSV
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(RESULTS_DIR, f"benchmark_{ts}.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "config", "threshold", "query", "n_filtered",
            "relevant@5", "relevant@10", "relevant@20",
            "mrr", "best_score", "median_score",
        ])
        writer.writeheader()
        writer.writerows(all_results)
    print(f"\nDetailed results saved to: {csv_path}")

    # Print summary recommendation
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    # Find best config per threshold
    for threshold in THRESHOLDS:
        th_results = [r for r in all_results if r["threshold"] == threshold]
        by_config = {}
        for r in th_results:
            cfg = r["config"]
            if cfg not in by_config:
                by_config[cfg] = []
            by_config[cfg].append(r)

        best_cfg = None
        best_mrr = -1
        for cfg, results in by_config.items():
            avg_mrr = np.mean([r["mrr"] for r in results])
            if avg_mrr > best_mrr:
                best_mrr = avg_mrr
                best_cfg = cfg

        avg_n = np.mean([r["n_filtered"] for r in by_config.get(best_cfg, [])])
        print(f"  threshold={threshold:.2f}: best={best_cfg} (MRR={best_mrr:.3f}, avg_results={avg_n:.0f})")


async def main():
    parser = argparse.ArgumentParser(description="Benchmark retrieval quality")
    parser.add_argument("--discover", action="store_true", help="Discovery mode: show top results")
    args = parser.parse_args()

    conn = await asyncpg.connect(DB_DSN)
    try:
        if args.discover:
            await discover_mode(conn)
        else:
            await benchmark_mode(conn)
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
