"""Typed raw_data models for each heritage type.

These dataclasses parse the JSONB ``raw_data`` column of ``heritage_assets``
into strongly-typed Python objects so that consumers (API, frontend) do not
need to know the original Solr field names.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ── Shared nested structures ────────────────────────────────────────────────


@dataclass(frozen=True)
class ImageInfo:
    id: str | None = None
    title: str | None = None
    author: str | None = None
    date: str | None = None
    url: str | None = None


@dataclass(frozen=True)
class BibliographyEntry:
    title: str | None = None
    author: str | None = None
    publisher: str | None = None
    year: str | None = None
    isbn: str | None = None
    pages: str | None = None
    location: str | None = None


@dataclass(frozen=True)
class TypologyInfo:
    typology: str | None = None
    style: str | None = None
    period: str | None = None
    chrono_start: str | None = None
    chrono_end: str | None = None


@dataclass(frozen=True)
class RelatedAsset:
    code: str | None = None
    denomination: str | None = None
    relation_type: str | None = None


# ── Inmueble ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class InmuebleRawData:
    code: str | None = None
    other_denominations: str | None = None
    characterisation: str | None = None
    postal_address: str | None = None
    historical_data: str | None = None
    description: str | None = None
    protection: str | None = None
    typologies: list[TypologyInfo] = field(default_factory=list)
    images: list[ImageInfo] = field(default_factory=list)
    bibliography: list[BibliographyEntry] = field(default_factory=list)
    related_assets: list[RelatedAsset] = field(default_factory=list)
    historical_periods: list[str] = field(default_factory=list)
    search_denominations: list[str] = field(default_factory=list)


# ── Mueble ──────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class MuebleRawData:
    code: str | None = None
    other_denominations: str | None = None
    characterisation: str | None = None
    measurements: str | None = None
    chronology: str | None = None
    description: str | None = None
    protection: str | None = None
    typologies: list[TypologyInfo] = field(default_factory=list)
    images: list[ImageInfo] = field(default_factory=list)
    bibliography: list[BibliographyEntry] = field(default_factory=list)
    related_assets: list[RelatedAsset] = field(default_factory=list)


# ── Inmaterial ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class InmaterialRawData:
    code: str | None = None
    other_denominations: str | None = None
    scope: str | None = None
    framework_activities: str | None = None
    activity_dates: str | None = None
    periodicity: str | None = None
    typologies_text: str | None = None
    district: str | None = None
    local_entity: str | None = None
    description: str | None = None
    development: str | None = None
    spatial_description: str | None = None
    agents_description: str | None = None
    evolution: str | None = None
    origins: str | None = None
    preparations: str | None = None
    clothing: str | None = None
    instruments: str | None = None
    transmission_mode: str | None = None
    transformations: str | None = None
    protection: str | None = None
    typologies: list[TypologyInfo] = field(default_factory=list)
    images: list[ImageInfo] = field(default_factory=list)
    bibliography: list[BibliographyEntry] = field(default_factory=list)
    related_assets: list[RelatedAsset] = field(default_factory=list)


# ── Paisaje ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PaisajeRawData:
    pdf_url: str | None = None
    search_terms: list[str] = field(default_factory=list)


# ── Parser ──────────────────────────────────────────────────────────────────


def _str(raw: dict, key: str) -> str | None:
    v = raw.get(key)
    if v is None or v == "":
        return None
    return str(v)


def _str_list(raw: dict, key: str) -> list[str]:
    v = raw.get(key)
    if not isinstance(v, list):
        return []
    return [str(x) for x in v if x is not None]


def _parse_images(raw: dict) -> list[ImageInfo]:
    ids = raw.get("imagen.id_img_smv") or []
    titles = raw.get("imagen.titulo_smv") or []
    authors = raw.get("imagen.autor_doc_smv") or []
    dates = raw.get("imagen.fec_ejecucion_smv") or []
    result = []
    for i, img_id in enumerate(ids):
        result.append(ImageInfo(
            id=str(img_id) if img_id else None,
            title=titles[i] if i < len(titles) else None,
            author=authors[i] if i < len(authors) else None,
            date=dates[i] if i < len(dates) else None,
            url=(
                f"https://guiadigital.iaph.es/sites/default/files/{img_id}"
                if img_id else None
            ),
        ))
    return result


def _parse_bibliography(raw: dict) -> list[BibliographyEntry]:
    titles = raw.get("bibliografia.titulo_smv") or []
    authors = raw.get("bibliografia.autor_smv") or []
    publishers = raw.get("bibliografia.editorial_smv") or []
    years = raw.get("bibliografia.a_o_smv") or []
    isbns = raw.get("bibliografia.isbn_issn_smv") or []
    pages = raw.get("bibliografia.pag_pub_smv") or []
    locations = raw.get("bibliografia.lugar_smv") or []
    result = []
    for i, title in enumerate(titles):
        result.append(BibliographyEntry(
            title=str(title) if title else None,
            author=str(authors[i]) if i < len(authors) and authors[i] else None,
            publisher=(
                str(publishers[i])
                if i < len(publishers) and publishers[i] else None
            ),
            year=str(years[i]) if i < len(years) and years[i] else None,
            isbn=str(isbns[i]) if i < len(isbns) and isbns[i] else None,
            pages=str(pages[i]) if i < len(pages) and pages[i] else None,
            location=(
                str(locations[i])
                if i < len(locations) and locations[i] else None
            ),
        ))
    return result


def _parse_typologies(raw: dict) -> list[TypologyInfo]:
    typols = raw.get("tipologia.den_tipologia_smv") or []
    styles = raw.get("tipologia.den_estilo_smv") or []
    periods = raw.get("tipologia.periodos_smv") or []
    starts = raw.get("tipologia.crono_ini_smv") or []
    ends = raw.get("tipologia.crono_fin_smv") or []
    result = []
    count = max(len(typols), len(styles), len(periods), 1) if (
        typols or styles or periods
    ) else 0
    for i in range(count):
        result.append(TypologyInfo(
            typology=str(typols[i]) if i < len(typols) and typols[i] else None,
            style=str(styles[i]) if i < len(styles) and styles[i] else None,
            period=str(periods[i]) if i < len(periods) and periods[i] else None,
            chrono_start=(
                str(starts[i]) if i < len(starts) and starts[i] else None
            ),
            chrono_end=(
                str(ends[i]) if i < len(ends) and ends[i] else None
            ),
        ))
    return result


def _parse_related_assets(raw: dict) -> list[RelatedAsset]:
    codes = raw.get("codigo.codigo_smv") or []
    denoms = raw.get("codigo.denominacion_smv") or []
    types = raw.get("codigo.tipo_smv") or []
    result = []
    for i, code in enumerate(codes):
        result.append(RelatedAsset(
            code=str(code) if code else None,
            denomination=(
                str(denoms[i]) if i < len(denoms) and denoms[i] else None
            ),
            relation_type=(
                str(types[i]) if i < len(types) and types[i] else None
            ),
        ))
    return result


def parse_raw_data(
    raw: dict,
    heritage_type: str,
) -> InmuebleRawData | MuebleRawData | InmaterialRawData | PaisajeRawData:
    """Parse a raw_data JSONB dict into a typed dataclass."""
    if heritage_type == "inmueble":
        return InmuebleRawData(
            code=_str(raw, "identifica.codigo_s"),
            other_denominations=_str(raw, "identifica.otr_denom_s"),
            characterisation=_str(raw, "identifica.caracterizacion_s"),
            postal_address=_str(raw, "identifica.dir_postal_s"),
            historical_data=_str(raw, "identifica.dat_historico_s"),
            description=_str(raw, "clob.descripcion_s"),
            protection=_str(raw, "proteccion_s"),
            typologies=_parse_typologies(raw),
            images=_parse_images(raw),
            bibliography=_parse_bibliography(raw),
            related_assets=_parse_related_assets(raw),
            historical_periods=_str_list(raw, "pHistorico_smv"),
            search_denominations=_str_list(raw, "busqueda_denominacion"),
        )
    elif heritage_type == "mueble":
        return MuebleRawData(
            code=_str(raw, "identifica.codigo_s"),
            other_denominations=_str(raw, "identifica.otr_denom_s"),
            characterisation=_str(raw, "identifica.caracterizacion_s"),
            measurements=_str(raw, "identifica.medidas_s"),
            chronology=_str(raw, "identifica.cronologia_s"),
            description=_str(raw, "clob.descripcion_s"),
            protection=_str(raw, "proteccion_s"),
            typologies=_parse_typologies(raw),
            images=_parse_images(raw),
            bibliography=_parse_bibliography(raw),
            related_assets=_parse_related_assets(raw),
        )
    elif heritage_type == "inmaterial":
        return InmaterialRawData(
            code=_str(raw, "identifica.codigo_s"),
            other_denominations=_str(raw, "identifica.otr_denom_s"),
            scope=_str(raw, "identifica.ambito_s"),
            framework_activities=_str(raw, "identifica.actmarco_s"),
            activity_dates=_str(raw, "identifica.fechasact_s"),
            periodicity=_str(raw, "identifica.periodicidad_s"),
            typologies_text=_str(raw, "identifica.tipologias_s"),
            district=_str(raw, "identifica.comarca_s"),
            local_entity=_str(raw, "identifica.entlocal_s"),
            description=_str(raw, "clob.descripcion_s"),
            development=_str(raw, "clob.desarrollo_s"),
            spatial_description=_str(raw, "clob.desc_espacio_s"),
            agents_description=_str(raw, "clob.descripcionagentes_s"),
            evolution=_str(raw, "clob.evolucion_s"),
            origins=_str(raw, "clob.origenes_s"),
            preparations=_str(raw, "clob.preparativos_s"),
            clothing=_str(raw, "clob.indumentaria_s"),
            instruments=_str(raw, "clob.instrumentos_s"),
            transmission_mode=_str(raw, "clob.modotransmision_s"),
            transformations=_str(raw, "clob.transformaciones_s"),
            protection=_str(raw, "proteccion_s"),
            typologies=_parse_typologies(raw),
            images=_parse_images(raw),
            bibliography=_parse_bibliography(raw),
            related_assets=_parse_related_assets(raw),
        )
    else:  # paisaje
        return PaisajeRawData(
            pdf_url=_str(raw, "pdf_url"),
            search_terms=_str_list(raw, "busqueda_generica"),
        )
