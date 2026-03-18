# Exploratory Data Analysis -- IAPH API Data (`heritage_assets`)

**Date:** 2026-03-16
**Source:** IAPH REST API (`https://guiadigital.iaph.es/api/1.0/`)
**Table:** `heritage_assets` (528 MB, 139,343 records)

---

## 1. Overview

The `heritage_assets` table stores structured data fetched from the IAPH public API. Each record represents a catalogued heritage asset in Andalusia, with a JSONB `raw_data` column preserving the full API response.

| Type | Total | % |
|------|------:|--:|
| **Patrimonio Mueble** (movable: artworks, objects) | 107,732 | 77.3% |
| **Patrimonio Inmueble** (immovable: buildings, sites) | 29,569 | 21.2% |
| **Patrimonio Inmaterial** (intangible: traditions, crafts) | 1,924 | 1.4% |
| **Paisaje Cultural** (cultural landscapes) | 118 | 0.1% |
| **TOTAL** | **139,343** | |

> The corpus is overwhelmingly dominated by **patrimonio mueble** (77%). Intangible heritage and cultural landscapes are comparatively scarce.

---

## 2. Structured field completeness

These are the columns extracted from the API into the relational schema:

| Type | Total | denomination | province | municipality | lat/lon | image_url | protection |
|------|------:|:-----------:|:--------:|:------------:|:-------:|:---------:|:----------:|
| mueble | 107,732 | 99.9% | 99.9% | 99.9% | **0%** | 66.1% | 99.9% |
| inmueble | 29,569 | 100% | 100% | 100% | **16.3%** | 46.3% | 100% |
| inmaterial | 1,924 | 100% | 100% | 100% | **0%** | 94.1% | 100% |
| paisaje | 118 | 100% | 100% | **0%** | **0%** | 100% | **0%** |

### Key gaps

- **Geolocation (lat/lon):** only **4,806 assets** (3.4%) have coordinates, all of type `inmueble`. Mueble, inmaterial, and paisaje have zero coordinates. This severely limits map-based features and route generation.
- **Images:** 86,821 assets (62%) have at least one image. Best coverage is inmaterial (94%) and paisaje (100%); worst is inmueble (46%).
- **Paisaje is the least enriched type:** no municipality, no coordinates, no protection status, and only 8 JSONB keys vs 60-110 for other types.
- **1 mueble record** has NULL denomination/province/municipality (likely a corrupt API record).

---

## 3. JSONB `raw_data` richness

Each heritage type has a very different internal schema. The number of JSONB keys per record is a proxy for data depth:

| Type | Avg keys | Min | Max |
|------|:--------:|:---:|:---:|
| inmaterial | 106 | 60 | 134 |
| inmueble | 74 | 29 | 110 |
| mueble | 63 | 2 | 114 |
| paisaje | 8 | 8 | 8 |

> Inmaterial is the most richly described type (avg 106 keys). Some mueble records have as few as 2 keys (essentially empty).

---

## 4. Patrimonio Inmueble -- deep analysis (29,569 records)

### 4.1 Core fields (100% coverage)

All records have: `denominacion`, `provincia`, `municipio`, `descripcion`, `dat_historico`, `dir_postal`, `caracterizacion`, `proteccion`, `codigo`, `otr_denom`, `estado`.

> This is the most complete and uniform type in the dataset.

### 4.2 Characterisation

| Characterisation | Count | % |
|-----------------|------:|--:|
| Arqueologica | 16,421 | 55.5% |
| Arquitectonica | 5,965 | 20.2% |
| Etnologica | 3,405 | 11.5% |
| Arquitectonica + Etnologica | 2,176 | 7.4% |
| Arqueologica + Arquitectonica | 1,249 | 4.2% |
| Other / empty | 353 | 1.2% |

> Over half of inmueble heritage is archaeological. Architectural sites are the second largest group.

### 4.3 Typologies (29,126 records -- 98.5%)

| Top typologies | Count |
|---------------|------:|
| Asentamientos (settlements) | 2,151 |
| Villae (Roman villas) | 1,452 |
| (empty) | 809 |
| Sitios con representaciones rupestres (rock art) | 624 |
| Construcciones funerarias (funerary) | 582 |
| Puentes (bridges) | 560 |
| Restos de artefactos | 549 |
| Cortijos (rural estates) | 458 |
| Dolmenes (dolmens) | 448 |
| Poblados (villages) | 437 |
| Iglesias (churches) | 420 |
| Ermitas (hermitages) | 389 |

> Note: 809 records have a blank typology value (`[" "]`), and 687 have duplicated values (`["Asentamientos", "Asentamientos"]`).

### 4.4 Historical periods (29,126 records)

| Top periods | Count |
|------------|------:|
| Edad Contemporanea | 5,104 |
| Epoca romana | 3,689 |
| (empty) | 2,938 |
| Edad Moderna | 1,858 |
| Edad Media | 1,505 |
| Prehistoria reciente | 1,102 |
| Edad del cobre | 923 |
| Alto imperio romano | 571 |

> 10% of period values are blanks (`[" "]`). Many records have multi-period arrays indicating assets spanning several eras.

### 4.5 Styles (29,126 records)

| Style | Count |
|-------|------:|
| **(empty)** | **18,436** |
| (2+ empty values) | 8,838 |
| Barroco | 243 |
| Racionalista | 129 |
| Mudejar | 121 |
| Renacimiento | 82 |
| Neoclasicismo | 66 |

> **94% of inmueble records have no style information.** The style field is essentially unpopulated -- only ~1,700 records have a meaningful value.

### 4.6 Additional enrichments

| Field | Records | Coverage |
|-------|--------:|--------:|
| Photos (foto.id_smv) | 29,560 | 99.9% |
| Typography | 29,126 | 98.5% |
| Description text | 28,144 | 95.2% |
| Chronology start (crono_ini) | 23,840 | 80.6% |
| Chronology end (crono_fin) | 25,909 | 87.6% |
| Bibliography | 13,357 | 45.2% |
| Protection details | 5,671 | 19.2% |

---

## 5. Patrimonio Mueble -- deep analysis (107,732 records)

### 5.1 Core fields

| Field | Present | Coverage |
|-------|--------:|--------:|
| denomination | 107,731 | >99.9% |
| province / municipality | 107,731 | >99.9% |
| chronology (text) | 107,731 | >99.9% |
| historical data | 107,731 | >99.9% |
| description (text) | 92,842 | **86.2%** |
| typology | 93,148 | 86.4% |
| materials | 92,511 | 85.8% |
| techniques | 92,566 | 85.9% |
| styles | 77,852 | 72.2% |
| iconography | 60,859 | 56.5% |
| bibliography | 33,385 | 31.0% |
| photos (foto.id_smv) | 8,809 | 8.2% |

> **14,890 mueble records (13.8%) have no description text at all.** Bibliography is only available for 31% of records.

### 5.2 Characterisation

| Characterisation | Count | % |
|-----------------|------:|--:|
| Etnologica | 102,395 | 95.0% |
| Sin Caracterizacion | 5,102 | 4.7% |
| Arqueologica | 131 | 0.1% |
| Other | 104 | 0.1% |

> 95% of movable heritage is classified as ethnological. 5,102 records (4.7%) have no characterisation.

### 5.3 Top typologies

| Typology | Count |
|----------|------:|
| Pinturas de caballete (easel paintings) | 10,805 |
| Esculturas de bulto redondo (freestanding sculptures) | 5,519 |
| Pinturas (paintings) | 4,195 |
| Fotografias | 2,928 |
| Relieves (reliefs) | 2,461 |
| Pinturas murales (murals) | 2,407 |
| Retablos (altarpieces) | 2,315 |
| Calices (chalices) | 1,380 |
| Azulejos (tiles) | 1,103 |
| Altorrelieves (high reliefs) | 1,102 |

### 5.4 Top materials

| Material | Count |
|----------|------:|
| Plata (silver) | 6,788 |
| Lienzo + pigmento al aceite (canvas + oil) | 6,577 |
| Madera + pigmento (wood + pigment) | 4,406 |
| Pigmento al aceite (oil pigment) | 3,995 |
| Madera (wood) | 2,813 |
| Marmol (marble) | 2,498 |
| Madera + pan de oro + pigmento (wood + gold leaf) | 2,277 |

### 5.5 Top styles

| Style | Count |
|-------|------:|
| Barroco | 41,682 |
| Neobarroco | 5,201 |
| Neoclasicismo | 5,087 |
| Renacimiento | 4,074 |
| Rococo | 3,232 |
| Manierismo | 3,205 |
| Arte contemporaneo | 2,625 |
| Eclecticista | 1,544 |
| Historicista | 1,042 |

> Unlike inmueble, mueble has rich style data. **Barroco dominates overwhelmingly** with 41K records (53% of those with style).

---

## 6. Patrimonio Inmaterial -- deep analysis (1,924 records)

### 6.1 Core fields (100% coverage, 100% non-empty)

All 1,924 records have fully populated: `descripcion`, `desarrollo`, `origenes`, `transformaciones`, `instrumentos`, `tipologias`, `periodicidad`, `fechasact`.

> This is the most uniformly complete type -- every record has all narrative fields filled in.

### 6.2 Top typologies

| Typology | Count |
|----------|------:|
| Procesion civico-religiosa | 150 |
| Produccion de alimentos | 145 |
| Semana Santa | 122 |
| Romeria | 111 |
| (empty) | 78 |
| Actividad festivo-ceremonial | 60 |
| Reposteria | 55 |
| Feria | 54 |
| Carnavales | 34 |
| Canciones | 34 |
| Alfareria (pottery) | 32 |
| Vinicultura (wine-making) | 32 |

> Religious processions, food production, and Semana Santa are the most catalogued intangible heritage types. Note the semicolon-separated multi-values (e.g., "Feria; Procesion civico-religiosa").

### 6.3 Protection

Only **75 of 1,924** (3.9%) inmaterial assets have formal protection.

---

## 7. Paisaje Cultural -- deep analysis (118 records)

The simplest type with only 8 JSONB keys: `id`, `tipo_contenido`, `provincia`, `provincia_smv`, `titulo`, `busqueda_generica`, `pdf_url`, `imagen_url`.

- All 118 records have a title, province, image URL, and PDF URL.
- **No municipality, no coordinates, no protection, no description text, no typology.**
- The full documentation of each landscape is in the linked PDF (not stored in DB).

---

## 8. Geographic distribution

### 8.1 By province

| Province | Inmueble | Mueble | Inmaterial | Paisaje | Total | % |
|----------|--------:|-------:|-----------:|--------:|------:|--:|
| Sevilla | 6,213 | 28,759 | 323 | 17 | 35,312 | 25.3% |
| Cordoba | 4,124 | 17,684 | 225 | 16 | 22,049 | 15.8% |
| Cadiz | 3,780 | 15,274 | 181 | 13 | 19,248 | 13.8% |
| Granada | 3,572 | 15,182 | 308 | 16 | 19,078 | 13.7% |
| Malaga | 2,724 | 13,256 | 231 | 11 | 16,222 | 11.6% |
| Jaen | 3,989 | 6,869 | 217 | 18 | 11,093 | 8.0% |
| Huelva | 2,691 | 5,415 | 245 | 15 | 8,366 | 6.0% |
| Almeria | 2,453 | 5,288 | 185 | 12 | 7,938 | 5.7% |

> Sevilla holds 25% of all assets. The top 4 provinces hold 69%. Jaen has the most even inmueble-to-mueble ratio, while Sevilla is heavily skewed toward mueble.

**Data quality issue:** 27 records have comma-separated multi-province values (e.g., "Huelva, Sevilla"). 1 mueble record has NULL province.

### 8.2 Top 10 municipalities

| Municipality | Province | Assets |
|-------------|----------|-------:|
| Sevilla | Sevilla | 22,278 |
| Cordoba | Cordoba | 12,754 |
| Granada | Granada | 9,599 |
| Malaga | Malaga | 6,067 |
| Cadiz | Cadiz | 5,703 |
| Almeria | Almeria | 3,838 |
| Antequera | Malaga | 3,516 |
| Jaen | Jaen | 3,479 |
| Linares | Jaen | 2,952 |
| Puerto Real | Cadiz | 2,292 |

> Provincial capitals dominate. Notably, Antequera (3.5K), Linares (3K), and Puerto Real (2.3K) are significant non-capital heritage hubs.

---

## 9. Data quality summary

### Strengths

1. **Large, well-structured corpus**: 139K assets with consistent JSONB schemas per type.
2. **Inmaterial is fully populated**: every record has all narrative fields filled -- ideal for RAG.
3. **Inmueble has 100% core field coverage**: denomination, province, municipality, description, historical data.
4. **Rich classification for mueble**: typology (86%), materials (86%), techniques (86%), styles (72%).
5. **Good image coverage overall**: 62% of all assets, 94% for inmaterial.

### Weaknesses

| Issue | Impact | Affected records |
|-------|--------|-----------------|
| **No coordinates for mueble/inmaterial/paisaje** | Route generation limited to ~5K inmueble | 134,537 (96.6%) |
| **Inmueble style field ~94% empty** | Style-based queries will return few inmueble results | ~27,400 |
| **Mueble description missing** | 14,890 records without description text | 14,890 (13.8%) |
| **Mueble records with 2 JSONB keys** | Essentially empty records | Unknown (min=2) |
| **Paisaje has no structured content** | Only PDF links, not queryable | 118 |
| **Multi-province values** | Breaks exact province filters | 27 |
| **Duplicated typology values** | Noise in typology arrays (e.g., same value x2) | ~687 inmueble |
| **Blank array values** | Typology/period/style arrays contain `[" "]` blanks | Widespread |

### Recommendations

1. **Geocoding fallback**: use municipality names to geocode the 96.6% of assets without coordinates (via Nominatim or similar).
2. **Clean blank array values**: strip `" "` entries from typology, period, and style arrays during ingestion or query time.
3. **Deduplicate typology arrays**: remove repeated values within the same record.
4. **Normalize multi-province records**: split into arrays or map to primary province.
5. **Flag empty mueble records**: identify and tag the records with minimal JSONB keys (<10) so they can be excluded or deprioritized.
6. **Extract paisaje PDF content**: parse the linked PDFs to enrich the 118 landscape records with searchable text.
