"""Analyze user feedback cross-referenced with search/route execution logs.

Parses rotated log files (feedback.log*, usecases/search.log*, usecases/routes.log*)
and produces structured JSON + CSV reports in logs/analysis/.

Works both inside Docker and locally — auto-detects log directory via LOG_DIR env var
or falls back to ../logs relative to this script.

Usage:
    uv run python scripts/analyze_feedback.py                  # all feedback
    uv run python scripts/analyze_feedback.py --since 2026-03-25  # from date
    uv run python scripts/analyze_feedback.py --negative-only     # thumbs-down only
"""

import argparse
import csv
import glob
import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime

# ── Log directory resolution ──────────────────────────────────────────────────
# Docker: LOG_DIR=/app/logs  |  Local: ../logs relative to this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LOG_DIR = os.path.join(SCRIPT_DIR, "..", "logs")
LOG_DIR = os.environ.get("LOG_DIR", DEFAULT_LOG_DIR)
ANALYSIS_DIR = os.path.join(LOG_DIR, "analysis")

# ── Regex patterns ────────────────────────────────────────────────────────────

# Common prefix: "2026-03-27 21:30:29 | INFO    | iaph.feedback | "
LOG_PREFIX = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"
    r" \| \w+\s*\| [\w.]+ \| "
)

# feedback.log patterns
RE_FEEDBACK = re.compile(
    r"Feedback submitted: user=(?P<user>\S+)"
    r" target_type=(?P<target_type>\S+)"
    r" target_id=(?P<target_id>\S+)"
    r" value=(?P<value>-?\d+)"
    r" metadata=(?P<metadata>.+)$"
)

# usecases/search.log patterns
RE_SEARCH_START = re.compile(
    r"Similarity search start: search_id=(?P<search_id>[0-9a-f-]+)"
    r" query=(?P<query>.+)$"
)

RE_SEARCH_RESULTS_SIM = re.compile(
    r"Search results \(similarity-only\): search_id=(?P<search_id>[0-9a-f-]+)"
    r" vector=(?P<vector>\d+), filtered=(?P<filtered>\d+),"
    r" threshold=(?P<threshold>[\d.]+)"
)

RE_SEARCH_RESULTS_HYBRID = re.compile(
    r"Search results: search_id=(?P<search_id>[0-9a-f-]+)"
    r" vector=(?P<vector>\d+), fts=(?P<fts>\d+),"
    r" fused=(?P<fused>\d+), filtered=(?P<filtered>\d+)"
)

RE_SEARCH_CHUNK = re.compile(
    r"(?:Similarity|Hybrid) #(?P<rank>\d+): search_id=(?P<search_id>[0-9a-f-]+)"
    r" score=(?P<score>[\d.]+) \| title: (?P<title>.+?)"
    r" \| type: (?P<heritage_type>\S+) \| province: (?P<province>.+)$"
)

RE_SEARCH_COMPLETE = re.compile(
    r"Similarity search complete: search_id=(?P<search_id>[0-9a-f-]+)"
    r" (?P<total>\d+) total, page (?P<page>\d+)/(?P<total_pages>\d+)"
    r" \((?P<chunks>\d+) chunks\)"
    r"(?: (?P<elapsed_ms>\d+)ms)?"
)

# usecases/routes.log patterns
RE_ROUTE_EXTRACTED = re.compile(
    r"Route generation: extracted_query=(?P<extracted_query>.+?)"
    r" from user_query=(?P<user_query>.+)$"
)

RE_ROUTE_RAG = re.compile(
    r"Route generation: RAG returned (?P<num_chunks>\d+) chunks"
    r" for query=(?P<query>.+)$"
)

RE_ROUTE_STOP = re.compile(
    r"Route stop #(?P<order>\d+): title=(?P<title>.+?)"
    r" \| type=(?P<heritage_type>\S+) \| province=(?P<province>.+)$"
)

RE_ROUTE_COMPLETE = re.compile(
    r"Route generation complete: route_id=(?P<route_id>\S+)"
    r" title=(?P<title>.+?) stops=(?P<stops>\d+)"
    r"(?: (?P<elapsed_ms>\d+)ms)?"
)

RE_ROUTE_API = re.compile(
    r"Route generated: id=(?P<route_id>\S+),"
    r" title=(?P<title>.+?), stops=(?P<stops>\d+),"
    r" duration=(?P<duration>\d+) min"
)


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class ChunkResult:
    rank: int
    score: float
    title: str
    heritage_type: str
    province: str


@dataclass
class SearchExecution:
    search_id: str
    timestamp: str = ""
    query: str = ""
    mode: str = ""  # "similarity-only" or "hybrid"
    vector_count: int = 0
    fts_count: int = 0
    fused_count: int = 0
    filtered_count: int = 0
    threshold: float = 0.0
    total_results: int = 0
    total_chunks: int = 0
    elapsed_ms: int = 0
    chunks: list[ChunkResult] = field(default_factory=list)


@dataclass
class RouteExecution:
    route_id: str
    timestamp: str = ""
    user_query: str = ""
    extracted_query: str = ""
    rag_chunks: int = 0
    stops: list[dict] = field(default_factory=list)
    title: str = ""
    num_stops: int = 0
    duration_min: int = 0
    elapsed_ms: int = 0


@dataclass
class FeedbackEntry:
    timestamp: str
    user: str
    target_type: str
    target_id: str
    value: int
    metadata: dict


# ── File discovery (handles rotation) ────────────────────────────────────────

def find_log_files(base_path: str) -> list[str]:
    """Find base log file + all rotated variants, sorted oldest first."""
    pattern = base_path + "*"
    files = glob.glob(pattern)
    # Sort: dated files first (chronological), then current file last
    dated = sorted(f for f in files if f != base_path)
    result = dated + ([base_path] if base_path in files else [])
    return result


def read_log_lines(base_path: str) -> list[str]:
    """Read all lines from a log file and its rotated variants."""
    lines = []
    for fpath in find_log_files(base_path):
        with open(fpath, encoding="utf-8", errors="replace") as f:
            lines.extend(f.readlines())
    return lines


def extract_timestamp(line: str) -> str:
    m = LOG_PREFIX.match(line)
    return m.group("timestamp") if m else ""


# ── Parsers ───────────────────────────────────────────────────────────────────

def parse_feedback(since: str | None = None) -> list[FeedbackEntry]:
    entries = []
    for line in read_log_lines(os.path.join(LOG_DIR, "feedback.log")):
        m = RE_FEEDBACK.search(line)
        if not m:
            continue
        ts = extract_timestamp(line)
        if since and ts < since:
            continue
        try:
            metadata = eval(m.group("metadata"))  # noqa: S307
        except Exception:
            metadata = {"raw": m.group("metadata")}
        entries.append(FeedbackEntry(
            timestamp=ts,
            user=m.group("user"),
            target_type=m.group("target_type"),
            target_id=m.group("target_id"),
            value=int(m.group("value")),
            metadata=metadata,
        ))
    return entries


def parse_search_logs(since: str | None = None) -> dict[str, SearchExecution]:
    """Parse search logs into a dict keyed by search_id."""
    executions: dict[str, SearchExecution] = {}
    for line in read_log_lines(
        os.path.join(LOG_DIR, "usecases", "search.log"),
    ):
        ts = extract_timestamp(line)
        if since and ts < since:
            continue

        # Search start
        m = RE_SEARCH_START.search(line)
        if m:
            sid = m.group("search_id")
            executions[sid] = SearchExecution(
                search_id=sid, timestamp=ts, query=m.group("query"),
            )
            continue

        # Results — similarity-only
        m = RE_SEARCH_RESULTS_SIM.search(line)
        if m:
            sid = m.group("search_id")
            if sid in executions:
                ex = executions[sid]
                ex.mode = "similarity-only"
                ex.vector_count = int(m.group("vector"))
                ex.filtered_count = int(m.group("filtered"))
                ex.threshold = float(m.group("threshold"))
            continue

        # Results — hybrid
        m = RE_SEARCH_RESULTS_HYBRID.search(line)
        if m:
            sid = m.group("search_id")
            if sid in executions:
                ex = executions[sid]
                ex.mode = "hybrid"
                ex.vector_count = int(m.group("vector"))
                ex.fts_count = int(m.group("fts"))
                ex.fused_count = int(m.group("fused"))
                ex.filtered_count = int(m.group("filtered"))
            continue

        # Individual chunk
        m = RE_SEARCH_CHUNK.search(line)
        if m:
            sid = m.group("search_id")
            if sid in executions:
                executions[sid].chunks.append(ChunkResult(
                    rank=int(m.group("rank")),
                    score=float(m.group("score")),
                    title=m.group("title").strip(),
                    heritage_type=m.group("heritage_type"),
                    province=m.group("province").strip(),
                ))
            continue

        # Completion
        m = RE_SEARCH_COMPLETE.search(line)
        if m:
            sid = m.group("search_id")
            if sid in executions:
                ex = executions[sid]
                ex.total_results = int(m.group("total"))
                ex.total_chunks = int(m.group("chunks"))
                if m.group("elapsed_ms"):
                    ex.elapsed_ms = int(m.group("elapsed_ms"))
            continue

    return executions


def parse_route_logs(since: str | None = None) -> dict[str, RouteExecution]:
    """Parse route logs into a dict keyed by route_id."""
    # We accumulate in current since route_id is only known at completion
    current: dict = {}
    executions: dict[str, RouteExecution] = {}

    for line in read_log_lines(
        os.path.join(LOG_DIR, "usecases", "routes.log"),
    ):
        ts = extract_timestamp(line)
        if since and ts < since:
            continue

        # Extracted query (start of a new generation)
        m = RE_ROUTE_EXTRACTED.search(line)
        if m:
            current = {
                "timestamp": ts,
                "user_query": m.group("user_query").strip().strip("'"),
                "extracted_query": m.group("extracted_query").strip().strip("'"),
                "stops": [],
                "rag_chunks": 0,
            }
            continue

        # RAG chunks
        m = RE_ROUTE_RAG.search(line)
        if m and current:
            current["rag_chunks"] = int(m.group("num_chunks"))
            continue

        # Stop detail
        m = RE_ROUTE_STOP.search(line)
        if m and current:
            current["stops"].append({
                "order": int(m.group("order")),
                "title": m.group("title").strip(),
                "heritage_type": m.group("heritage_type"),
                "province": m.group("province").strip(),
            })
            continue

        # Route complete (from use case — has timing)
        m = RE_ROUTE_COMPLETE.search(line)
        if m:
            rid = m.group("route_id").rstrip(",")
            route = RouteExecution(
                route_id=rid,
                timestamp=current.get("timestamp", ts),
                user_query=current.get("user_query", ""),
                extracted_query=current.get("extracted_query", ""),
                rag_chunks=current.get("rag_chunks", 0),
                stops=current.get("stops", []),
                title=m.group("title").strip().strip("'"),
                num_stops=int(m.group("stops")),
                elapsed_ms=int(m.group("elapsed_ms")) if m.group("elapsed_ms") else 0,
            )
            executions[rid] = route
            current = {}
            continue

        # Route generated (from API layer — has duration, fallback for older logs)
        m = RE_ROUTE_API.search(line)
        if m:
            rid = m.group("route_id").rstrip(",")
            if rid not in executions:
                executions[rid] = RouteExecution(
                    route_id=rid,
                    timestamp=ts,
                    title=m.group("title").strip().strip("'"),
                    num_stops=int(m.group("stops")),
                    duration_min=int(m.group("duration")),
                )
            else:
                executions[rid].duration_min = int(m.group("duration"))
            continue

    return executions


# ── Report generation ─────────────────────────────────────────────────────────

@dataclass
class SearchReport:
    """One row per feedback entry for a search."""
    timestamp: str
    user: str
    value: int
    search_id: str
    query: str
    mode: str
    vector_count: int
    fts_count: int
    fused_count: int
    filtered_count: int
    total_results: int
    elapsed_ms: int
    num_chunks_returned: int
    avg_score: float
    min_score: float
    max_score: float
    top_chunk_title: str
    top_chunk_type: str
    top_chunk_province: str
    results: str  # JSON array: [{rank, score, title, type, province}, ...]
    metadata_query: str
    metadata_filters: str


@dataclass
class SearchChunkReport:
    """One row per chunk in a search that received feedback."""
    search_id: str
    query: str
    feedback_value: int
    rank: int
    score: float
    title: str
    heritage_type: str
    province: str


@dataclass
class RouteReport:
    """One row per feedback entry for a route."""
    timestamp: str
    user: str
    value: int
    route_id: str
    user_query: str
    extracted_query: str
    title: str
    rag_chunks: int
    num_stops: int
    duration_min: int
    elapsed_ms: int
    stop_titles: str
    stop_types: str
    stop_provinces: str


def build_search_reports(
    feedbacks: list[FeedbackEntry],
    searches: dict[str, SearchExecution],
) -> tuple[list[SearchReport], list[SearchChunkReport]]:
    summary_rows: list[SearchReport] = []
    chunk_rows: list[SearchChunkReport] = []

    for fb in feedbacks:
        if fb.target_type != "search":
            continue
        ex = searches.get(fb.target_id)
        if ex:
            scores = [c.score for c in ex.chunks] if ex.chunks else [0.0]
            top = ex.chunks[0] if ex.chunks else ChunkResult(0, 0, "", "", "")
            summary_rows.append(SearchReport(
                timestamp=fb.timestamp,
                user=fb.user,
                value=fb.value,
                search_id=fb.target_id,
                query=ex.query,
                mode=ex.mode,
                vector_count=ex.vector_count,
                fts_count=ex.fts_count,
                fused_count=ex.fused_count,
                filtered_count=ex.filtered_count,
                total_results=ex.total_results,
                elapsed_ms=ex.elapsed_ms,
                num_chunks_returned=len(ex.chunks),
                avg_score=sum(scores) / len(scores),
                min_score=min(scores),
                max_score=max(scores),
                top_chunk_title=top.title,
                top_chunk_type=top.heritage_type,
                top_chunk_province=top.province,
                results=json.dumps(
                    [{"rank": c.rank, "score": c.score, "title": c.title,
                      "type": c.heritage_type, "province": c.province}
                     for c in ex.chunks],
                    ensure_ascii=False,
                ),
                metadata_query=fb.metadata.get("query", ""),
                metadata_filters=json.dumps(
                    fb.metadata.get("filters", []), ensure_ascii=False,
                ),
            ))
            for chunk in ex.chunks:
                chunk_rows.append(SearchChunkReport(
                    search_id=fb.target_id,
                    query=ex.query,
                    feedback_value=fb.value,
                    rank=chunk.rank,
                    score=chunk.score,
                    title=chunk.title,
                    heritage_type=chunk.heritage_type,
                    province=chunk.province,
                ))
        else:
            # Feedback without matching search log (may be pre-search_id era)
            summary_rows.append(SearchReport(
                timestamp=fb.timestamp,
                user=fb.user,
                value=fb.value,
                search_id=fb.target_id,
                query="",
                mode="unknown",
                vector_count=0, fts_count=0, fused_count=0, filtered_count=0,
                total_results=0, elapsed_ms=0, num_chunks_returned=0,
                avg_score=0, min_score=0, max_score=0,
                top_chunk_title="", top_chunk_type="", top_chunk_province="",
                results="[]",
                metadata_query=fb.metadata.get("query", ""),
                metadata_filters=json.dumps(
                    fb.metadata.get("filters", []), ensure_ascii=False,
                ),
            ))
    return summary_rows, chunk_rows


def build_route_reports(
    feedbacks: list[FeedbackEntry],
    routes: dict[str, RouteExecution],
) -> list[RouteReport]:
    rows: list[RouteReport] = []
    for fb in feedbacks:
        if fb.target_type != "route":
            continue
        ex = routes.get(fb.target_id)
        if ex:
            rows.append(RouteReport(
                timestamp=fb.timestamp,
                user=fb.user,
                value=fb.value,
                route_id=fb.target_id,
                user_query=ex.user_query,
                extracted_query=ex.extracted_query,
                title=ex.title,
                rag_chunks=ex.rag_chunks,
                num_stops=ex.num_stops,
                duration_min=ex.duration_min,
                elapsed_ms=ex.elapsed_ms,
                stop_titles=" | ".join(s.get("title", "") for s in ex.stops),
                stop_types=" | ".join(s.get("heritage_type", "") for s in ex.stops),
                stop_provinces=" | ".join(s.get("province", "") for s in ex.stops),
            ))
        else:
            rows.append(RouteReport(
                timestamp=fb.timestamp,
                user=fb.user,
                value=fb.value,
                route_id=fb.target_id,
                user_query="", extracted_query="", title="",
                rag_chunks=0, num_stops=0, duration_min=0, elapsed_ms=0,
                stop_titles="", stop_types="", stop_provinces="",
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


def write_json(data: list | dict, filepath: str) -> None:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def print_summary(
    feedbacks: list[FeedbackEntry],
    search_reports: list[SearchReport],
    chunk_reports: list[SearchChunkReport],
    route_reports: list[RouteReport],
) -> None:
    total = len(feedbacks)
    positive = sum(1 for f in feedbacks if f.value > 0)
    negative = sum(1 for f in feedbacks if f.value < 0)

    print(f"\n{'=' * 60}")
    print(f"  FEEDBACK ANALYSIS REPORT — {datetime.now():%Y-%m-%d %H:%M}")
    print(f"{'=' * 60}")
    print(f"  Total feedback entries:  {total}")
    print(f"  Positive (👍):           {positive}")
    print(f"  Negative (👎):           {negative}")
    if total:
        print(f"  Satisfaction rate:       {100 * positive / total:.1f}%")

    # Search breakdown
    s_fb = [f for f in feedbacks if f.target_type == "search"]
    if s_fb:
        s_pos = sum(1 for f in s_fb if f.value > 0)
        s_neg = sum(1 for f in s_fb if f.value < 0)
        matched = sum(1 for r in search_reports if r.mode != "unknown")
        print(f"\n  SEARCH ({len(s_fb)} entries, {matched} matched with logs)")
        print(f"    Positive: {s_pos}  |  Negative: {s_neg}")
        if search_reports:
            neg_reports = [r for r in search_reports if r.value < 0 and r.mode != "unknown"]
            pos_reports = [r for r in search_reports if r.value > 0 and r.mode != "unknown"]
            if neg_reports:
                avg_neg = sum(r.avg_score for r in neg_reports) / len(neg_reports)
                avg_neg_results = sum(r.total_results for r in neg_reports) / len(neg_reports)
                print(f"    Negative avg score:    {avg_neg:.4f}")
                print(f"    Negative avg results:  {avg_neg_results:.1f}")
            if pos_reports:
                avg_pos = sum(r.avg_score for r in pos_reports) / len(pos_reports)
                avg_pos_results = sum(r.total_results for r in pos_reports) / len(pos_reports)
                print(f"    Positive avg score:    {avg_pos:.4f}")
                print(f"    Positive avg results:  {avg_pos_results:.1f}")

    # Route breakdown
    r_fb = [f for f in feedbacks if f.target_type == "route"]
    if r_fb:
        r_pos = sum(1 for f in r_fb if f.value > 0)
        r_neg = sum(1 for f in r_fb if f.value < 0)
        matched = sum(1 for r in route_reports if r.title)
        print(f"\n  ROUTES ({len(r_fb)} entries, {matched} matched with logs)")
        print(f"    Positive: {r_pos}  |  Negative: {r_neg}")

    print(f"\n  Output: {ANALYSIS_DIR}/")
    print(f"{'=' * 60}\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze RAG feedback from logs")
    parser.add_argument(
        "--since", type=str, default=None,
        help="Only include entries from this date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--negative-only", action="store_true",
        help="Only analyze negative feedback",
    )
    args = parser.parse_args()

    print(f"Reading logs from: {os.path.abspath(LOG_DIR)}")

    # Parse all sources
    feedbacks = parse_feedback(since=args.since)
    if args.negative_only:
        feedbacks = [f for f in feedbacks if f.value < 0]

    if not feedbacks:
        print("No feedback entries found.")
        return

    searches = parse_search_logs(since=args.since)
    routes = parse_route_logs(since=args.since)

    print(f"Parsed: {len(feedbacks)} feedback, {len(searches)} searches, {len(routes)} routes")

    # Build reports
    search_reports, chunk_reports = build_search_reports(feedbacks, searches)
    route_reports = build_route_reports(feedbacks, routes)

    # Write outputs
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    if search_reports:
        write_csv(search_reports, os.path.join(ANALYSIS_DIR, f"search_feedback_{ts}.csv"))
    if chunk_reports:
        write_csv(chunk_reports, os.path.join(ANALYSIS_DIR, f"search_chunks_{ts}.csv"))
    if route_reports:
        write_csv(route_reports, os.path.join(ANALYSIS_DIR, f"route_feedback_{ts}.csv"))

    # Full JSON with all detail
    full_report = {
        "generated_at": datetime.now().isoformat(),
        "filters": {"since": args.since, "negative_only": args.negative_only},
        "summary": {
            "total_feedback": len(feedbacks),
            "positive": sum(1 for f in feedbacks if f.value > 0),
            "negative": sum(1 for f in feedbacks if f.value < 0),
            "search_feedback": len(search_reports),
            "route_feedback": len(route_reports),
            "search_executions_matched": sum(
                1 for r in search_reports if r.mode != "unknown"
            ),
            "route_executions_matched": sum(1 for r in route_reports if r.title),
        },
        "search_feedback": [asdict(r) for r in search_reports],
        "search_chunks": [asdict(r) for r in chunk_reports],
        "route_feedback": [asdict(r) for r in route_reports],
    }
    write_json(full_report, os.path.join(ANALYSIS_DIR, f"feedback_report_{ts}.json"))

    print_summary(feedbacks, search_reports, chunk_reports, route_reports)


if __name__ == "__main__":
    main()
