"""Benchmark embedding service latency via the search/similarity endpoint.

Usage:
    cd backend
    uv run python scripts/benchmark_embedding.py [--n 20] [--label baseline]

Requires the backend API to be running. Authenticates with admin credentials
from config/.env and measures round-trip latency for each request.
"""

import argparse
import json
import statistics
import time

import httpx

from src.config import settings

API_BASE = f"http://localhost:18080{settings.api_v1_prefix}"
QUERY = "cuevas del sacromonte"


def get_token() -> str:
    """Login and return JWT access token."""
    resp = httpx.post(
        f"{API_BASE}/auth/login",
        json={"username": settings.admin_username, "password": settings.admin_password},
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def run_benchmark(n: int, token: str) -> list[float]:
    """Run n requests and return latencies in ms."""
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"query": QUERY, "page": 1, "page_size": 1}
    latencies = []

    for i in range(n):
        start = time.perf_counter()
        resp = httpx.post(
            f"{API_BASE}/search/similarity",
            json=payload,
            headers=headers,
            timeout=120.0,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        latencies.append(elapsed_ms)

        status = "OK" if resp.status_code == 200 else f"ERR {resp.status_code}"
        print(f"  [{i+1:3d}/{n}] {elapsed_ms:8.1f} ms  {status}")

    return latencies


def print_stats(label: str, latencies: list[float]) -> dict:
    """Print and return stats."""
    sorted_lat = sorted(latencies)
    stats = {
        "label": label,
        "n": len(latencies),
        "min": round(min(latencies), 1),
        "max": round(max(latencies), 1),
        "mean": round(statistics.mean(latencies), 1),
        "p50": round(sorted_lat[len(sorted_lat) // 2], 1),
        "p95": round(sorted_lat[int(len(sorted_lat) * 0.95)], 1),
    }

    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")
    print(f"  Requests: {stats['n']}")
    print(f"  Min:      {stats['min']:>8.1f} ms")
    print(f"  Max:      {stats['max']:>8.1f} ms")
    print(f"  Mean:     {stats['mean']:>8.1f} ms")
    print(f"  p50:      {stats['p50']:>8.1f} ms")
    print(f"  p95:      {stats['p95']:>8.1f} ms")
    print(f"{'=' * 60}\n")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Benchmark embedding latency")
    parser.add_argument("--n", type=int, default=20, help="Number of requests")
    parser.add_argument("--label", type=str, default="baseline", help="Label for this run")
    parser.add_argument("--output", type=str, default="scripts/results/benchmark.jsonl",
                        help="JSONL file to append results")
    args = parser.parse_args()

    print(f"Authenticating as {settings.admin_username}...")
    token = get_token()

    print(f"Running {args.n} requests to {API_BASE}/search/similarity")
    print(f"Query: {QUERY!r}\n")

    latencies = run_benchmark(args.n, token)
    stats = print_stats(args.label, latencies)

    # Append to JSONL
    with open(args.output, "a") as f:
        f.write(json.dumps(stats) + "\n")
    print(f"Results appended to {args.output}")


if __name__ == "__main__":
    main()
