"""List all search and route queries with their RAG results.

Parses rotated log files (usecases/search.log*, usecases/routes.log*)
and produces CSV reports in logs/analysis/ with every execution and its results.

Works both inside Docker and locally — auto-detects log directory via LOG_DIR env var
or falls back to ../logs relative to this script.

Usage:
    uv run python scripts/analyze_queries.py                     # all queries
    uv run python scripts/analyze_queries.py --since 2026-03-25  # from date
    uv run python scripts/analyze_queries.py --type search       # only searches
    uv run python scripts/analyze_queries.py --type route        # only routes
"""

import argparse
import csv
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime

from scripts.analyze_feedback import (
    ANALYSIS_DIR,
    LOG_DIR,
    UserLookup,
    build_user_lookup,
    parse_feedback,
    parse_route_logs,
    parse_search_logs,
)

# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class SearchQueryRow:
    """One row per search execution."""
    timestamp: str
    user_id: str
    profile_type: str
    search_id: str
    query: str
    filters: str
    mode: str
    vector_count: int
    fts_count: int
    fused_count: int
    filtered_count: int
    total_results: int
    total_chunks: int
    elapsed_ms: int
    num_results_logged: int
    avg_score: float
    min_score: float
    max_score: float
    results: str  # JSON array with all chunks
    feedback_value: str  # "+1", "-1", or "" if no feedback


@dataclass
class RouteQueryRow:
    """One row per route generation."""
    timestamp: str
    user_id: str
    profile_type: str
    route_id: str
    user_query: str
    extracted_query: str
    title: str
    rag_chunks: int
    num_stops: int
    duration_min: int
    elapsed_ms: int
    stops: str  # JSON array with stop details
    feedback_value: str


# ── Report builders ───────────────────────────────────────────────────────────

def build_search_query_rows(
    searches: dict,
    feedback_map: dict[str, int],
    user_lookup: UserLookup | None = None,
) -> list[SearchQueryRow]:
    rows = []
    _lu = user_lookup or UserLookup({}, {})
    for sid, ex in sorted(searches.items(), key=lambda kv: kv[1].timestamp):
        scores = [c.score for c in ex.chunks] if ex.chunks else []
        fb = feedback_map.get(sid)
        username = _lu.resolve_username(ex.user)
        rows.append(SearchQueryRow(
            timestamp=ex.timestamp,
            user_id=username,
            profile_type=_lu.resolve_profile(username),
            search_id=sid,
            query=ex.query,
            filters=ex.filters,
            mode=ex.mode,
            vector_count=ex.vector_count,
            fts_count=ex.fts_count,
            fused_count=ex.fused_count,
            filtered_count=ex.filtered_count,
            total_results=ex.total_results,
            total_chunks=ex.total_chunks,
            elapsed_ms=ex.elapsed_ms,
            num_results_logged=len(ex.chunks),
            avg_score=sum(scores) / len(scores) if scores else 0.0,
            min_score=min(scores) if scores else 0.0,
            max_score=max(scores) if scores else 0.0,
            results=json.dumps(
                [{"rank": c.rank, "score": c.score, "title": c.title,
                  "type": c.heritage_type, "province": c.province}
                 for c in ex.chunks],
                ensure_ascii=False,
            ),
            feedback_value=str(fb) if fb is not None else "",
        ))
    return rows


def build_route_query_rows(
    routes: dict,
    feedback_map: dict[str, int],
    user_lookup: UserLookup | None = None,
) -> list[RouteQueryRow]:
    rows = []
    _lu = user_lookup or UserLookup({}, {})
    for rid, ex in sorted(routes.items(), key=lambda kv: kv[1].timestamp):
        fb = feedback_map.get(rid)
        username = _lu.resolve_username(ex.user)
        rows.append(RouteQueryRow(
            timestamp=ex.timestamp,
            user_id=username,
            profile_type=_lu.resolve_profile(username),
            route_id=rid,
            user_query=ex.user_query,
            extracted_query=ex.extracted_query,
            title=ex.title,
            rag_chunks=ex.rag_chunks,
            num_stops=ex.num_stops,
            duration_min=ex.duration_min,
            elapsed_ms=ex.elapsed_ms,
            stops=json.dumps(ex.stops, ensure_ascii=False),
            feedback_value=str(fb) if fb is not None else "",
        ))
    return rows


# ── Output ────────────────────────────────────────────────────────────────────

def write_csv(rows: list, filepath: str) -> None:
    if not rows:
        return
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    fieldnames = list(asdict(rows[0]).keys())
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def print_summary(
    search_rows: list[SearchQueryRow],
    route_rows: list[RouteQueryRow],
) -> None:
    print(f"\n{'=' * 60}")
    print(f"  QUERY ANALYSIS REPORT — {datetime.now():%Y-%m-%d %H:%M}")
    print(f"{'=' * 60}")

    if search_rows:
        with_fb = [r for r in search_rows if r.feedback_value]
        scores = [r.avg_score for r in search_rows if r.avg_score > 0]
        times = [r.elapsed_ms for r in search_rows if r.elapsed_ms > 0]
        print(f"\n  SEARCHES: {len(search_rows)} total")
        print(f"    With feedback:    {len(with_fb)}")
        if scores:
            print(f"    Avg score:        {sum(scores) / len(scores):.4f}")
        if times:
            print(f"    Avg time:         {sum(times) / len(times):.0f}ms")
        zero = sum(1 for r in search_rows if r.total_results == 0)
        if zero:
            print(f"    Zero results:     {zero}")

    if route_rows:
        with_fb = [r for r in route_rows if r.feedback_value]
        times = [r.elapsed_ms for r in route_rows if r.elapsed_ms > 0]
        print(f"\n  ROUTES: {len(route_rows)} total")
        print(f"    With feedback:    {len(with_fb)}")
        if times:
            print(f"    Avg time:         {sum(times) / len(times):.0f}ms")

    print(f"\n  Output: {ANALYSIS_DIR}/")
    print(f"{'=' * 60}\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="List all search/route queries with RAG results",
    )
    parser.add_argument(
        "--since", type=str, default=None,
        help="Only include entries from this date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--type", type=str, choices=["search", "route"], default=None,
        help="Only analyze this query type",
    )
    args = parser.parse_args()

    print(f"Reading logs from: {os.path.abspath(LOG_DIR)}")

    # Build feedback lookup: target_id → value
    feedbacks = parse_feedback(since=args.since)
    feedback_map = {fb.target_id: fb.value for fb in feedbacks}

    # Build user profile lookup from DB
    user_lookup = build_user_lookup()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    search_rows: list[SearchQueryRow] = []
    route_rows: list[RouteQueryRow] = []

    if args.type in (None, "search"):
        searches = parse_search_logs(since=args.since)
        search_rows = build_search_query_rows(searches, feedback_map, user_lookup)
        if search_rows:
            write_csv(
                search_rows,
                os.path.join(ANALYSIS_DIR, f"all_searches_{ts}.csv"),
            )
        print(f"Searches parsed: {len(search_rows)}")

    if args.type in (None, "route"):
        routes = parse_route_logs(since=args.since)
        route_rows = build_route_query_rows(routes, feedback_map, user_lookup)
        if route_rows:
            write_csv(
                route_rows,
                os.path.join(ANALYSIS_DIR, f"all_routes_{ts}.csv"),
            )
        print(f"Routes parsed: {len(route_rows)}")

    print_summary(search_rows, route_rows)


if __name__ == "__main__":
    main()
