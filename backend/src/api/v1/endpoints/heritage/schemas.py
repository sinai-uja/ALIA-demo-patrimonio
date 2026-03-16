from pydantic import BaseModel, Field


class ImageInfoSchema(BaseModel):
    id: str | None = None
    title: str | None = None
    author: str | None = None
    date: str | None = None
    url: str | None = None


class BibliographyEntrySchema(BaseModel):
    title: str | None = None
    author: str | None = None
    publisher: str | None = None
    year: str | None = None
    isbn: str | None = None
    pages: str | None = None
    location: str | None = None


class TypologyInfoSchema(BaseModel):
    typology: str | None = None
    style: str | None = None
    period: str | None = None
    chrono_start: str | None = None
    chrono_end: str | None = None


class RelatedAssetSchema(BaseModel):
    code: str | None = None
    denomination: str | None = None
    relation_type: str | None = None


# ── Type-specific details ───────────────────────────────────────────────────


class InmuebleDetailsSchema(BaseModel):
    type: str = "inmueble"
    code: str | None = None
    other_denominations: str | None = None
    characterisation: str | None = None
    postal_address: str | None = None
    historical_data: str | None = None
    description: str | None = None
    protection: str | None = None
    typologies: list[TypologyInfoSchema] = []
    images: list[ImageInfoSchema] = []
    bibliography: list[BibliographyEntrySchema] = []
    related_assets: list[RelatedAssetSchema] = []
    historical_periods: list[str] = []


class MuebleDetailsSchema(BaseModel):
    type: str = "mueble"
    code: str | None = None
    other_denominations: str | None = None
    characterisation: str | None = None
    measurements: str | None = None
    chronology: str | None = None
    description: str | None = None
    protection: str | None = None
    typologies: list[TypologyInfoSchema] = []
    images: list[ImageInfoSchema] = []
    bibliography: list[BibliographyEntrySchema] = []
    related_assets: list[RelatedAssetSchema] = []


class InmaterialDetailsSchema(BaseModel):
    type: str = "inmaterial"
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
    typologies: list[TypologyInfoSchema] = []
    images: list[ImageInfoSchema] = []
    bibliography: list[BibliographyEntrySchema] = []
    related_assets: list[RelatedAssetSchema] = []


class PaisajeDetailsSchema(BaseModel):
    type: str = "paisaje"
    pdf_url: str | None = None
    search_terms: list[str] = []


DetailsSchema = (
    InmuebleDetailsSchema
    | MuebleDetailsSchema
    | InmaterialDetailsSchema
    | PaisajeDetailsSchema
)


# ── Asset schemas ───────────────────────────────────────────────────────────


class HeritageAssetSchema(BaseModel):
    id: str
    heritage_type: str
    denomination: str | None = None
    province: str | None = None
    municipality: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    image_url: str | None = None
    image_ids: list[str] = []
    protection: str | None = None
    details: DetailsSchema | None = None


class HeritageAssetListSchema(BaseModel):
    items: list[HeritageAssetSchema]
    total: int
    limit: int
    offset: int


class HeritageAssetSummarySchema(BaseModel):
    """Lightweight schema for list views (no details)."""

    id: str
    heritage_type: str
    denomination: str | None = None
    province: str | None = None
    municipality: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    image_url: str | None = None
    protection: str | None = None


class HeritageAssetSummaryListSchema(BaseModel):
    items: list[HeritageAssetSummarySchema]
    total: int = Field(description="Total matching assets")
    limit: int
    offset: int
