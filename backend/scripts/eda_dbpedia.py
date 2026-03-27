"""EDA: DBpedia references in heritage_assets.raw_data JSONB.

Scans the raw_data column to find DBpedia URIs and linked-data fields,
categorises them by heritage_type and JSON path, and generates a markdown report.

Usage:
    cd backend && uv run python scripts/eda_dbpedia.py
"""

import asyncio
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime

import asyncpg

DB_DSN = "postgresql://uja:uja@localhost:15432/uja_iaph"
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
DBPEDIA_RE = re.compile(r"https?://(?:\w+\.)?dbpedia\.org/\S+")
LINKED_DATA_KEYS = {"@id", "@type", "rdfs:label", "foaf:name", "schema:name",
                     "prov:wasAssociatedWith", "prov:wasDerivedFrom"}


def walk_json(obj, path="$"):
    """Recursively yield (path, key, value) for every leaf in a JSON structure."""
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


def find_dbpedia_refs(raw_data: dict) -> list[dict]:
    """Find all DBpedia URI references in a raw_data dict."""
    refs = []
    for path, key, value in walk_json(raw_data):
        if isinstance(value, str) and DBPEDIA_RE.search(value):
            uris = DBPEDIA_RE.findall(value)
            for uri in uris:
                refs.append({"path": path, "key": key, "uri": uri})
        elif isinstance(value, str) and "dbpedia" in value.lower():
            refs.append({"path": path, "key": key, "uri": value})
    return refs


def find_linked_data_fields(raw_data: dict) -> list[dict]:
    """Find all linked-data fields (@id, @type, rdfs:label, etc.)."""
    fields = []
    for path, key, value in walk_json(raw_data):
        if key in LINKED_DATA_KEYS:
            fields.append({"path": path, "key": key, "value": str(value)[:200]})
    return fields


def categorise_uri(path: str, uri: str) -> str:
    """Categorise a DBpedia URI based on its JSON path context."""
    path_lower = path.lower()
    if "municipio" in path_lower:
        return "municipio"
    if "provincia" in path_lower:
        return "provincia"
    if "tipologia" in path_lower:
        return "tipologia"
    if "periodo" in path_lower or "phistorico" in path_lower or "crono" in path_lower:
        return "periodo_historico"
    if "identifica" in path_lower:
        return "identificacion_activo"
    return "otro"


async def main():
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
        total = sum(r["cnt"] for r in type_counts)
        print(f"Total heritage_assets: {total:,}")
        for r in type_counts:
            print(f"  {r['heritage_type']}: {r['cnt']:,}")

        # 2. Scan raw_data for DBpedia and linked-data fields
        all_dbpedia_refs = defaultdict(list)  # heritage_type -> list of refs
        all_linked_data = defaultdict(list)
        top_level_keys = defaultdict(Counter)  # heritage_type -> Counter of keys
        sample_raw = {}  # heritage_type -> first raw_data sample

        for ht_row in type_counts:
            ht = ht_row["heritage_type"]
            print(f"\nScanning {ht}...")

            rows = await conn.fetch("""
                SELECT id, denomination, raw_data
                FROM heritage_assets
                WHERE heritage_type = $1
            """, ht)

            for row in rows:
                raw = row["raw_data"]
                if isinstance(raw, str):
                    raw = json.loads(raw)

                # Top-level keys
                if isinstance(raw, dict):
                    for k in raw.keys():
                        top_level_keys[ht][k] += 1

                    # Save first sample
                    if ht not in sample_raw:
                        sample_raw[ht] = {
                            "id": row["id"],
                            "denomination": row["denomination"],
                            "keys": list(raw.keys())[:50],
                        }

                    # DBpedia refs
                    refs = find_dbpedia_refs(raw)
                    if refs:
                        all_dbpedia_refs[ht].extend(refs)

                    # Linked data fields
                    ld_fields = find_linked_data_fields(raw)
                    if ld_fields:
                        all_linked_data[ht].extend(ld_fields)

            dbp_count = len(all_dbpedia_refs.get(ht, []))
            ld_count = len(all_linked_data.get(ht, []))
            print(f"  {ht}: {len(rows)} assets, {dbp_count} DBpedia refs, {ld_count} LD fields")

        # 3. Aggregate DBpedia stats
        dbpedia_by_category = defaultdict(Counter)  # category -> Counter of URI patterns
        dbpedia_by_path = Counter()  # path pattern -> count
        unique_uris = set()

        for ht, refs in all_dbpedia_refs.items():
            for ref in refs:
                cat = categorise_uri(ref["path"], ref["uri"])
                # Generalise URI to pattern (strip specific resource name)
                dbpedia_by_category[cat][ref["uri"]] += 1
                # Generalise path: remove array indices
                gen_path = re.sub(r"\[\d+\]", "[*]", ref["path"])
                dbpedia_by_path[gen_path] += 1
                unique_uris.add(ref["uri"])

        # 4. Aggregate linked-data stats
        ld_by_key = defaultdict(Counter)  # key -> Counter of values
        for ht, fields in all_linked_data.items():
            for field in fields:
                ld_by_key[field["key"]][field["value"][:100]] += 1

        # 5. Generate report
        os.makedirs(RESULTS_DIR, exist_ok=True)
        report_path = os.path.join(RESULTS_DIR, "eda_dbpedia.md")

        lines = []
        lines.append("# EDA: Referencias DBpedia en heritage_assets.raw_data")
        lines.append(f"\n**Fecha**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"**Total assets**: {total:,}")
        lines.append("")

        # Summary table
        lines.append("## 1. Assets por heritage_type")
        lines.append("")
        lines.append("| heritage_type | count | DBpedia refs | Linked-data fields |")
        lines.append("|---|---|---|---|")
        for r in type_counts:
            ht = r["heritage_type"]
            dbp = len(all_dbpedia_refs.get(ht, []))
            ld = len(all_linked_data.get(ht, []))
            lines.append(f"| {ht} | {r['cnt']:,} | {dbp:,} | {ld:,} |")
        lines.append("")

        # DBpedia findings
        lines.append("## 2. Referencias DBpedia encontradas")
        lines.append("")
        if not unique_uris:
            lines.append("**No se encontraron URIs DBpedia en el raw_data almacenado.**")
            lines.append("")
            lines.append(
                "Esto confirma que los datos en `heritage_assets.raw_data` provienen del "
                "**endpoint Solr plano** de la API IAPH (`/api/1.0/busqueda/...`), "
                "que usa campos aplanados (`identifica.denominacion_s`, "
                "`tipologia.den_tipologia_smv`, etc.) "
                "sin objetos JSON-LD con `@id`/`@type`."
            )
            lines.append("")
            lines.append(
                "El JSON con referencias DBpedia que se muestra en la documentacion "
                "proviene de un **endpoint diferente** (detalle individual del activo), "
                "que devuelve la estructura nested con linked data "
                "(`municipio.@id`, `provincia.@id`, etc.)."
            )
        else:
            lines.append(f"**{len(unique_uris)} URIs DBpedia unicas encontradas.**")
            lines.append("")

            # By category
            lines.append("### Por categoria semantica")
            lines.append("")
            lines.append("| Categoria | URIs unicas | Ocurrencias | Ejemplo |")
            lines.append("|---|---|---|---|")
            for cat in sorted(dbpedia_by_category.keys()):
                uris = dbpedia_by_category[cat]
                total_occ = sum(uris.values())
                example = uris.most_common(1)[0][0] if uris else ""
                lines.append(f"| {cat} | {len(uris)} | {total_occ:,} | `{example[:80]}` |")
            lines.append("")

            # By path
            lines.append("### Por JSON path")
            lines.append("")
            lines.append("| JSON path (generalizado) | Ocurrencias |")
            lines.append("|---|---|")
            for path, count in dbpedia_by_path.most_common(30):
                lines.append(f"| `{path}` | {count:,} |")
            lines.append("")

            # Sample URIs
            lines.append("### Muestra de URIs")
            lines.append("")
            for cat in sorted(dbpedia_by_category.keys()):
                lines.append(f"**{cat}**:")
                for uri, count in dbpedia_by_category[cat].most_common(10):
                    lines.append(f"- `{uri}` ({count:,} ocurrencias)")
                lines.append("")

        # Linked data fields
        lines.append("## 3. Campos linked-data (@id, @type, rdfs:label, etc.)")
        lines.append("")
        if not any(all_linked_data.values()):
            lines.append("**No se encontraron campos linked-data** (`@id`, `@type`, `rdfs:label`, "
                         "`foaf:name`, `schema:name`, `prov:wasAssociatedWith`).")
            lines.append("")
            lines.append("Esto confirma el formato Solr plano sin objetos JSON-LD.")
        else:
            for key in sorted(ld_by_key.keys()):
                vals = ld_by_key[key]
                lines.append(f"### `{key}` ({sum(vals.values()):,} ocurrencias)")
                lines.append("")
                for val, count in vals.most_common(15):
                    lines.append(f"- `{val}` ({count:,})")
                lines.append("")

        # Top-level keys by type
        lines.append("## 4. Top-level keys en raw_data por heritage_type")
        lines.append("")
        for ht in sorted(top_level_keys.keys()):
            keys = top_level_keys[ht]
            lines.append(f"### {ht} ({sum(1 for _ in keys)} campos unicos)")
            lines.append("")
            lines.append("| Campo | Assets con este campo |")
            lines.append("|---|---|")
            for k, count in keys.most_common():
                lines.append(f"| `{k}` | {count:,} |")
            lines.append("")

        # Sample raw_data
        lines.append("## 5. Muestra de raw_data (primer asset por tipo)")
        lines.append("")
        for ht, sample in sorted(sample_raw.items()):
            lines.append(f"### {ht}: {sample['denomination']}")
            lines.append(f"- **ID**: `{sample['id']}`")
            lines.append(f"- **Keys** ({len(sample['keys'])}): "
                         f"`{'`, `'.join(sample['keys'])}`")
            lines.append("")

        # Conclusion
        lines.append("## 6. Conclusion")
        lines.append("")
        if not unique_uris:
            lines.append("Los datos almacenados en `heritage_assets.raw_data` **no contienen "
                         "referencias DBpedia**. El formato Solr plano usado por el endpoint de "
                         "busqueda masiva no incluye objetos JSON-LD.")
            lines.append("")
            lines.append("Las referencias DBpedia mostradas en la documentacion de la API IAPH "
                         "(e.g. `municipio.@id: http://es.dbpedia.org/resource/Cortes_de_Baza`) "
                         "solo aparecen en el **endpoint de detalle individual** del activo, no "
                         "en la respuesta de busqueda Solr que alimenta nuestra base de datos.")
            lines.append("")
            lines.append("### Opciones para obtener datos DBpedia:")
            lines.append("")
            lines.append("1. **Fetch individual**: usar el endpoint de detalle de la API IAPH "
                         "para cada activo (muy lento, ~132K requests)")
            lines.append("2. **Construir URIs**: generar las URIs DBpedia a partir de los nombres "
                         "de municipio/provincia ya almacenados "
                         "(e.g. `http://es.dbpedia.org/resource/{municipio}`)")
            lines.append("3. **SPARQL query**: consultar es.dbpedia.org directamente con los "
                         "nombres de activos para encontrar entidades enlazadas")
        else:
            lines.append("Se encontraron referencias DBpedia en los datos almacenados. "
                         "Ver secciones 2 y 3 para el analisis detallado.")

        report = "\n".join(lines) + "\n"

        with open(report_path, "w") as f:
            f.write(report)

        print(f"\nReport written to: {report_path}")
        print(f"DBpedia URIs found: {len(unique_uris)}")
        print(f"Linked-data fields found: {sum(sum(v.values()) for v in ld_by_key.values())}")

    finally:
        await conn.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except asyncpg.PostgresError as e:
        print(f"ERROR: Database error: {e}")
        sys.exit(1)
