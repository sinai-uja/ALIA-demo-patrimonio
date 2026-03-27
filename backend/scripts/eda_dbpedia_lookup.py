"""EDA: Query IAPH enriched API endpoint for DBpedia references.

Fetches individual asset detail from the IAPH enriched endpoint and extracts
all DBpedia URIs, categorising them by JSON path (municipio, provincia,
tipología, periodo, or the heritage asset itself).

Usage:
    cd backend && uv run python scripts/eda_dbpedia_lookup.py
    cd backend && uv run python scripts/eda_dbpedia_lookup.py --sample 1000
    cd backend && uv run python scripts/eda_dbpedia_lookup.py --resume
"""

import argparse
import asyncio
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime

import asyncpg
import httpx

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DB_DSN = "postgresql://uja:uja@localhost:15432/uja_iaph"
API_BASE = "https://guiadigital.iaph.es/api/1.0/bien"
TOKEN = os.environ.get("IAPH_API_TOKEN", "ebe7d5fd-e77c-3581-8242-6eb6a5dbdbef")

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
CSV_PATH = os.path.join(RESULTS_DIR, "dbpedia_iaph_matches.csv")
CHECKPOINT_PATH = os.path.join(RESULTS_DIR, "dbpedia_lookup_checkpoint.json")
REPORT_PATH = os.path.join(RESULTS_DIR, "eda_dbpedia_lookup.md")
SAMPLES_DIR = os.path.join(RESULTS_DIR, "dbpedia_samples")

SAMPLE_SIZE = 10_000
SEED = 42  # reproducible sampling — PostgreSQL setseed() range: -1.0 to 1.0
DELAY = 0.4  # ~2.5 req/s
CHECKPOINT_EVERY = 500
MAX_RETRIES = 3

DBPEDIA_RE = re.compile(r"https?://(?:\w+\.)?dbpedia\.org/\S+")

# Heritage type (DB value) → API path segment
TYPE_MAP = {
    "inmueble": "inmueble",
    "mueble": "mueble",
    "inmaterial": "inmaterial",
    "paisaje": "paisaje",
}


# ---------------------------------------------------------------------------
# JSON walking & categorisation
# ---------------------------------------------------------------------------
def walk_json(obj, path="$"):
    """Recursively yield (path, key, value) for every node in a JSON structure."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            child_path = f"{path}.{k}"
            yield child_path, k, v
            yield from walk_json(v, child_path)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            child_path = f"{path}[{i}]"
            yield child_path, None, item
            yield from walk_json(item, child_path)


def extract_dbpedia_refs(data: dict) -> list[dict]:
    """Extract all DBpedia URI references from an enriched API response."""
    refs = []
    for path, key, value in walk_json(data):
        if not isinstance(value, str):
            continue
        # Direct @id or prov:wasAssociatedWith with DBpedia URI
        if DBPEDIA_RE.search(value):
            for uri in DBPEDIA_RE.findall(value):
                category = categorise_by_path(path, uri)
                refs.append({"path": path, "key": key, "uri": uri, "category": category})
    return refs


def categorise_by_path(path: str, uri: str) -> str:
    """Categorise a DBpedia URI based on its JSON path context.

    Categories:
      - municipio / provincia: geographic auxiliary entities
      - tipologia_dbpedia: typology concepts (Ciudad, Asentamiento...)
      - periodo_dbpedia: historical periods (Alto Imperio romano...)
      - etnia_dbpedia: ethnic/cultural groups (Iberos...)
      - entidad_descripcion: NER entities extracted from description text
        (Resources[].@URI in identifica.descripcion or clob.descripcion)
        — these may reference the asset itself or related concepts
      - foto_geo: geographic refs inside photo metadata
      - context_ns: JSON-LD namespace prefixes (not real refs, filtered out)
      - otro: anything else
    """
    p = path.lower()

    # JSON-LD context namespace prefixes — not actual entity refs
    if ".context." in p:
        return "context_ns"

    # NER entities in description text — potentially about the asset itself
    if "descripcion" in p and "resources" in p and "@uri" in p:
        return "entidad_descripcion"

    # Photo metadata — geographic duplicates
    if "fotolist" in p:
        if "municipio" in p:
            return "foto_geo"
        if "provincia" in p:
            return "foto_geo"
        return "foto_otro"

    # Municipality / Province (most common auxiliary)
    if "municipio" in p and "@id" in p:
        return "municipio"
    if "provincia" in p and "@id" in p:
        return "provincia"

    # Etnia/cultura linked to DBpedia
    if "etnia" in p and "wasassociatedwith" in p:
        return "etnia_dbpedia"

    # Tipología linked to DBpedia via prov:wasAssociatedWith
    if "tipologia" in p and "wasassociatedwith" in p:
        return "tipologia_dbpedia"
    if "tipologia" in p and "@id" in p:
        return "tipologia_iaph"

    # Periodo histórico linked to DBpedia
    if ("periodo" in p or "phistorico" in p or "crono" in p) and "wasassociatedwith" in p:
        return "periodo_dbpedia"
    if ("periodo" in p or "phistorico" in p or "crono" in p) and "@id" in p:
        return "periodo_iaph"

    # Generic wasAssociatedWith
    if "wasassociatedwith" in p:
        return "asociacion_dbpedia"

    # wasDerivedFrom
    if "wasderivedfrom" in p:
        return "derivacion_dbpedia"

    return "otro"


# ---------------------------------------------------------------------------
# API fetching
# ---------------------------------------------------------------------------
async def fetch_enriched(
    client: httpx.AsyncClient,
    heritage_type_api: str,
    asset_id: str,
) -> dict | None:
    """Fetch enriched detail for a single asset. Returns parsed JSON or None."""
    # The ID in the DB may be like "14980" — use as-is
    numeric_id = asset_id.split("-")[-1] if "-" in asset_id else asset_id
    url = f"{API_BASE}/{heritage_type_api}/enriquecido/{numeric_id}"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {TOKEN}",
    }

    for attempt in range(MAX_RETRIES):
        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 401:
                return "TOKEN_EXPIRED"
            if resp.status_code == 404:
                return None
            # Some assets return 500 — the enrichment sub-service fails.
            # If 500 body is an error object (has "status"/"error" keys), treat as unavailable.
            if resp.status_code == 500:
                try:
                    data = resp.json()
                    if "error" in data or "status" in data:
                        return "UNAVAILABLE"
                except (json.JSONDecodeError, ValueError):
                    pass
                return "UNAVAILABLE"
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            wait = DELAY * (2 ** attempt)
            print(f"  HTTP {e.response.status_code} for {url}, "
                  f"retry {attempt+1}/{MAX_RETRIES}")
            await asyncio.sleep(wait)
        except httpx.RequestError as e:
            wait = DELAY * (2 ** attempt)
            print(f"  Request error for {url}: {str(e)[:80]}, "
                  f"retry {attempt+1}/{MAX_RETRIES}")
            await asyncio.sleep(wait)
    return None


# ---------------------------------------------------------------------------
# Checkpoint management
# ---------------------------------------------------------------------------
def load_checkpoint() -> set:
    """Load set of already-processed asset IDs from checkpoint file."""
    if not os.path.exists(CHECKPOINT_PATH):
        return set()
    with open(CHECKPOINT_PATH) as f:
        data = json.load(f)
    return set(data.get("processed_ids", []))


def save_checkpoint(processed_ids: set):
    """Save processed asset IDs to checkpoint."""
    with open(CHECKPOINT_PATH, "w") as f:
        json.dump({"processed_ids": list(processed_ids), "count": len(processed_ids)}, f)


def load_existing_csv() -> list[dict]:
    """Load existing CSV results for resume."""
    if not os.path.exists(CSV_PATH):
        return []
    rows = []
    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main(sample_size: int = SAMPLE_SIZE, resume: bool = False, seed: int = SEED):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(SAMPLES_DIR, exist_ok=True)

    print("Connecting to database...")
    conn = await asyncpg.connect(DB_DSN)

    try:
        # 1. Count assets by type
        type_counts = await conn.fetch("""
            SELECT heritage_type, count(*) as cnt
            FROM heritage_assets
            GROUP BY heritage_type
            ORDER BY heritage_type
        """)
        total_db = sum(r["cnt"] for r in type_counts)
        print(f"Total heritage_assets in DB: {total_db:,}")
        for r in type_counts:
            print(f"  {r['heritage_type']}: {r['cnt']:,}")

        # 2. Stratified sample
        # Proportional sampling, but take all paisaje (only ~118)
        type_weights = {}
        for r in type_counts:
            ht = r["heritage_type"]
            if ht == "paisaje":
                type_weights[ht] = r["cnt"]  # take all
            else:
                type_weights[ht] = r["cnt"]

        # Calculate proportional sizes
        non_paisaje_total = sum(c for ht, c in type_weights.items() if ht != "paisaje")
        paisaje_count = type_weights.get("paisaje", 0)
        remaining = sample_size - min(paisaje_count, sample_size)

        sample_sizes = {}
        for ht, cnt in type_weights.items():
            if ht == "paisaje":
                sample_sizes[ht] = min(cnt, sample_size)
            else:
                sample_sizes[ht] = min(cnt, round(remaining * cnt / non_paisaje_total))

        actual_sample = sum(sample_sizes.values())
        print(f"\nSample sizes (total={actual_sample:,}):")
        for ht, n in sample_sizes.items():
            print(f"  {ht}: {n:,}")

        # 3. Query assets (reproducible with setseed)
        pg_seed = (seed % 1000) / 1000.0  # map int seed to PostgreSQL range [0, 1)
        await conn.execute(f"SELECT setseed({pg_seed})")
        assets = []
        for ht, n in sample_sizes.items():
            rows = await conn.fetch("""
                SELECT id, heritage_type, denomination
                FROM heritage_assets
                WHERE heritage_type = $1
                ORDER BY random()
                LIMIT $2
            """, ht, n)
            assets.extend(rows)
            print(f"  Selected {len(rows)} from {ht}")

        print(f"\nTotal assets to query: {len(assets):,}")

    finally:
        await conn.close()

    # 4. Resume support
    processed_ids = set()
    csv_rows = []
    if resume:
        processed_ids = load_checkpoint()
        csv_rows = load_existing_csv()
        print(f"Resuming: {len(processed_ids)} already processed, {len(csv_rows)} CSV rows loaded")

    # Filter out already-processed
    pending = [a for a in assets if a["id"] not in processed_ids]
    print(f"Pending: {len(pending):,} assets to fetch")

    # 5. Fetch enriched data
    stats = {
        "total": len(assets),
        "fetched": len(processed_ids),
        "with_dbpedia": 0,
        "errors": 0,
        "not_found": 0,  # 404
        "unavailable": 0,  # 500 — enrichment service fails for this asset
        "token_expired": False,
    }
    samples_saved = 0

    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        for i, asset in enumerate(pending):
            asset_id = asset["id"]
            ht = asset["heritage_type"]
            api_type = TYPE_MAP.get(ht)
            if not api_type:
                print(f"  Unknown heritage_type: {ht}, skipping {asset_id}")
                stats["errors"] += 1
                continue

            result = await fetch_enriched(client, api_type, str(asset_id))

            if result == "TOKEN_EXPIRED":
                print(f"\n*** TOKEN EXPIRED at asset {i+1}/{len(pending)} ***")
                print("Saving progress and generating partial report...")
                stats["token_expired"] = True
                break

            processed_ids.add(asset_id)
            stats["fetched"] += 1

            # Per-asset debug line
            denom_short = (asset["denomination"] or "?")[:50]
            if result == "UNAVAILABLE":
                stats["unavailable"] += 1
                status_tag = "500"
                dbp_count = 0
            elif result is None:
                stats["not_found"] += 1
                status_tag = "404"
                dbp_count = 0
            else:
                # Save a few JSON samples for the report
                if samples_saved < 5:
                    sample_path = os.path.join(
                        SAMPLES_DIR, f"{api_type}_{asset_id}.json"
                    )
                    with open(sample_path, "w") as f:
                        json.dump(result, f, indent=2, ensure_ascii=False)
                    samples_saved += 1

                # Extract DBpedia refs
                refs = extract_dbpedia_refs(result)
                dbp_count = len(refs)
                if refs:
                    stats["with_dbpedia"] += 1
                    for ref in refs:
                        csv_rows.append({
                            "asset_id": asset_id,
                            "denomination": asset["denomination"],
                            "heritage_type": ht,
                            "json_path": ref["path"],
                            "category": ref["category"],
                            "dbpedia_uri": ref["uri"],
                        })
                status_tag = "OK"

            done = stats["fetched"]
            api_url = f"{API_BASE}/{api_type}/enriquecido/{asset_id}"
            print(
                f"  [{done:,}/{len(assets):,}] {status_tag} | {denom_short} "
                f"| dbpedia:{dbp_count} | {api_url}",
                flush=True,
            )

            # Checkpoint
            if done % CHECKPOINT_EVERY == 0:
                save_checkpoint(processed_ids)
                _write_csv(csv_rows)
                print(f"  (checkpoint saved: {done:,} processed)")

            # Rate limiting
            await asyncio.sleep(DELAY)

    # 6. Final save
    save_checkpoint(processed_ids)
    _write_csv(csv_rows)
    print(f"\nFetch complete: {stats['fetched']:,} assets processed")

    # 7. Generate report
    generate_report(csv_rows, stats, sample_sizes)
    print(f"Report: {REPORT_PATH}")
    print(f"CSV:    {CSV_PATH}")


def _write_csv(rows: list[dict]):
    """Write CSV results."""
    if not rows:
        return
    fieldnames = ["asset_id", "denomination", "heritage_type", "json_path", "category",
                  "dbpedia_uri"]
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def generate_report(csv_rows: list[dict], stats: dict, sample_sizes: dict):
    """Generate markdown report from collected data."""
    lines = []
    lines.append("# EDA: DBpedia en endpoint enriquecido IAPH")
    lines.append(f"\n**Fecha**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Assets consultados**: {stats['fetched']:,} / {stats['total']:,}")
    if stats["token_expired"]:
        lines.append("**NOTA**: Token expirado, informe parcial.")
    lines.append("")

    # -- Summary --
    lines.append("## 1. Resumen")
    lines.append("")
    lines.append(f"- Assets con al menos 1 URI DBpedia: **{stats['with_dbpedia']:,}** "
                 f"({_pct(stats['with_dbpedia'], stats['fetched'])})")
    lines.append(f"- Total URIs DBpedia encontradas: **{len(csv_rows):,}**")
    lines.append(f"- Assets no disponibles (500 — enrichment falla): {stats['unavailable']:,}")
    lines.append(f"- Assets no encontrados (404): {stats['not_found']:,}")
    lines.append(f"- Errores: {stats['errors']:,}")
    lines.append("")

    # -- By heritage type --
    lines.append("## 2. Assets con DBpedia por heritage_type")
    lines.append("")
    lines.append("| heritage_type | Consultados | Con DBpedia | % | URIs totales |")
    lines.append("|---|---|---|---|---|")

    by_type = defaultdict(lambda: {"assets": set(), "uris": 0})
    for row in csv_rows:
        by_type[row["heritage_type"]]["assets"].add(row["asset_id"])
        by_type[row["heritage_type"]]["uris"] += 1

    for ht in sorted(sample_sizes.keys()):
        queried = sample_sizes[ht]
        info = by_type.get(ht, {"assets": set(), "uris": 0})
        with_dbp = len(info["assets"])
        lines.append(
            f"| {ht} | {queried:,} | {with_dbp:,} | {_pct(with_dbp, queried)} | {info['uris']:,} |"
        )
    lines.append("")

    # -- By category --
    lines.append("## 3. Desglose por categoría semántica")
    lines.append("")
    cat_counter = Counter()
    cat_unique_uris = defaultdict(set)
    for row in csv_rows:
        cat_counter[row["category"]] += 1
        cat_unique_uris[row["category"]].add(row["dbpedia_uri"])

    lines.append("| Categoría | Ocurrencias | URIs únicas | Ejemplo |")
    lines.append("|---|---|---|---|")
    for cat, count in cat_counter.most_common():
        uris = cat_unique_uris[cat]
        example = next(iter(uris)) if uris else ""
        lines.append(f"| {cat} | {count:,} | {len(uris):,} | `{example[:80]}` |")
    lines.append("")

    # -- Top-30 URIs --
    lines.append("## 4. Top-30 URIs DBpedia más frecuentes")
    lines.append("")
    uri_counter = Counter(row["dbpedia_uri"] for row in csv_rows)
    lines.append("| URI | Ocurrencias | Categoría |")
    lines.append("|---|---|---|")
    # Build category lookup
    uri_cat = {}
    for row in csv_rows:
        uri_cat.setdefault(row["dbpedia_uri"], row["category"])
    for uri, count in uri_counter.most_common(30):
        lines.append(f"| `{uri}` | {count:,} | {uri_cat.get(uri, '')} |")
    lines.append("")

    # -- Assets with their own DBpedia URI --
    lines.append("## 5. Assets con URI DBpedia del propio activo")
    lines.append("")
    # Check for identificacion or "otro" categories that might be the asset itself
    asset_self_refs = [
        row for row in csv_rows
        if row["category"] in ("identificacion", "otro", "asociacion_dbpedia", "derivacion_dbpedia")
    ]
    if asset_self_refs:
        # Group by asset
        by_asset = defaultdict(list)
        for row in asset_self_refs:
            by_asset[row["asset_id"]].append(row)
        lines.append(f"**{len(by_asset)} assets** con posibles URIs DBpedia propias:")
        lines.append("")
        for asset_id, rows in list(by_asset.items())[:20]:  # show max 20
            denom = rows[0]["denomination"]
            lines.append(f"- **{denom}** (`{asset_id}`, {rows[0]['heritage_type']})")
            for r in rows:
                lines.append(f"  - `{r['json_path']}` → `{r['dbpedia_uri']}`")
        if len(by_asset) > 20:
            lines.append(f"  - ... y {len(by_asset) - 20} más (ver CSV)")
    else:
        lines.append("**No se encontraron URIs DBpedia que referencien al propio activo.**")
        lines.append("")
        lines.append("Todas las URIs DBpedia encontradas referencian entidades auxiliares "
                     "(municipios, provincias, tipologías, periodos).")
    lines.append("")

    # -- JSON path patterns --
    lines.append("## 6. JSON paths donde aparecen URIs DBpedia")
    lines.append("")
    path_counter = Counter()
    for row in csv_rows:
        # Generalise: remove array indices
        gen_path = re.sub(r"\[\d+\]", "[*]", row["json_path"])
        path_counter[gen_path] += 1
    lines.append("| JSON path (generalizado) | Ocurrencias |")
    lines.append("|---|---|")
    for path, count in path_counter.most_common(30):
        lines.append(f"| `{path}` | {count:,} |")
    lines.append("")

    # -- Sample JSON --
    lines.append("## 7. Muestras de respuesta JSON-LD")
    lines.append("")
    sample_files = []
    if os.path.exists(SAMPLES_DIR):
        sample_files = sorted(os.listdir(SAMPLES_DIR))[:3]
    if sample_files:
        for fname in sample_files:
            fpath = os.path.join(SAMPLES_DIR, fname)
            with open(fpath) as f:
                sample_json = json.load(f)
            # Only show a relevant excerpt (top-level keys + first few nested)
            lines.append(f"### {fname}")
            lines.append("")
            lines.append("```json")
            excerpt = json.dumps(sample_json, indent=2, ensure_ascii=False)
            # Truncate to ~200 lines
            excerpt_lines = excerpt.split("\n")
            if len(excerpt_lines) > 200:
                lines.extend(excerpt_lines[:200])
                lines.append(f"  // ... truncado ({len(excerpt_lines)} líneas totales)")
            else:
                lines.append(excerpt)
            lines.append("```")
            lines.append("")
    else:
        lines.append("No se guardaron muestras JSON.")
    lines.append("")

    # -- Conclusion --
    lines.append("## 8. Conclusión")
    lines.append("")
    total_with = stats["with_dbpedia"]
    total_fetched = stats["fetched"]
    if total_with == 0:
        lines.append("El endpoint enriquecido de la API IAPH **no devuelve URIs DBpedia** "
                     "para los activos consultados.")
    else:
        pct = _pct(total_with, total_fetched)
        lines.append(f"El **{pct}** de los activos consultados ({total_with:,}/{total_fetched:,}) "
                     f"incluye al menos una URI DBpedia en su respuesta enriquecida.")
        lines.append("")

        # Check if any are "self" references
        self_cats = {"identificacion", "otro", "asociacion_dbpedia", "derivacion_dbpedia"}
        self_count = len({r["asset_id"] for r in csv_rows if r["category"] in self_cats})
        aux_cats = {"municipio", "provincia", "tipologia_dbpedia", "periodo_dbpedia"}  # noqa: F841

        lines.append("### Tipos de referencia:")
        lines.append("")
        if self_count:
            lines.append(f"- **{self_count:,} assets** tienen URIs DBpedia que podrían "
                        "referenciar al propio activo patrimonial (categorías: identificación, "
                        "asociación, derivación, otro)")
        lines.append("- Las URIs DBpedia más comunes son de **entidades auxiliares**: "
                     "municipios, provincias, tipologías y periodos históricos")
        lines.append("")
        lines.append("### Valor para el corpus:")
        lines.append("")
        lines.append("1. **Enriquecimiento geográfico**: URIs de municipios y provincias permiten "
                     "enlazar con datos geográficos de DBpedia (coordenadas, población, etc.)")
        lines.append("2. **Enriquecimiento tipológico**: URIs de tipologías permiten mapear "
                     "categorías IAPH a conceptos estándar de la ontología DBpedia")
        lines.append("3. **Enriquecimiento temporal**: URIs de periodos históricos vinculan "
                     "a la descripción en DBpedia del periodo")
        if self_count:
            lines.append(
                f"4. **Enlace directo**: {self_count} activos tienen referencia "
                "DBpedia propia, permitiendo acceder a información "
                "complementaria en Wikipedia/DBpedia"
            )

    report = "\n".join(lines) + "\n"
    with open(REPORT_PATH, "w") as f:
        f.write(report)


def _pct(n: int, total: int) -> str:
    if total == 0:
        return "0%"
    return f"{100 * n / total:.1f}%"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def cli():
    parser = argparse.ArgumentParser(
        description="Query IAPH enriched API for DBpedia references in heritage assets."
    )
    parser.add_argument(
        "--sample", type=int, default=SAMPLE_SIZE,
        help=f"Number of assets to sample (default: {SAMPLE_SIZE})",
    )
    parser.add_argument(
        "--seed", type=int, default=SEED,
        help=f"Random seed for reproducible sampling (default: {SEED})",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Resume from last checkpoint",
    )
    parser.add_argument(
        "--token", default=None,
        help="Override Bearer token (default: env IAPH_API_TOKEN or built-in)",
    )
    args = parser.parse_args()

    if args.token:
        global TOKEN
        TOKEN = args.token

    asyncio.run(main(sample_size=args.sample, resume=args.resume, seed=args.seed))


if __name__ == "__main__":
    try:
        cli()
    except KeyboardInterrupt:
        print("\nInterrupted. Progress saved at checkpoint.")
        sys.exit(1)
