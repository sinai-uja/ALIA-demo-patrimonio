from dataclasses import dataclass, field


@dataclass(frozen=True)
class ImageInfoDTO:
    id: str | None = None
    title: str | None = None
    author: str | None = None
    date: str | None = None
    url: str | None = None


@dataclass(frozen=True)
class BibliographyEntryDTO:
    title: str | None = None
    author: str | None = None
    publisher: str | None = None
    year: str | None = None
    isbn: str | None = None
    pages: str | None = None
    location: str | None = None


@dataclass(frozen=True)
class TypologyInfoDTO:
    typology: str | None = None
    style: str | None = None
    period: str | None = None
    chrono_start: str | None = None
    chrono_end: str | None = None


@dataclass(frozen=True)
class RelatedAssetDTO:
    code: str | None = None
    denomination: str | None = None
    relation_type: str | None = None


@dataclass(frozen=True)
class InmuebleDetailsDTO:
    type: str = "inmueble"
    code: str | None = None
    other_denominations: str | None = None
    characterisation: str | None = None
    postal_address: str | None = None
    historical_data: str | None = None
    description: str | None = None
    protection: str | None = None
    typologies: list[TypologyInfoDTO] = field(default_factory=list)
    images: list[ImageInfoDTO] = field(default_factory=list)
    bibliography: list[BibliographyEntryDTO] = field(default_factory=list)
    related_assets: list[RelatedAssetDTO] = field(default_factory=list)
    historical_periods: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MuebleDetailsDTO:
    type: str = "mueble"
    code: str | None = None
    other_denominations: str | None = None
    characterisation: str | None = None
    measurements: str | None = None
    chronology: str | None = None
    description: str | None = None
    protection: str | None = None
    typologies: list[TypologyInfoDTO] = field(default_factory=list)
    images: list[ImageInfoDTO] = field(default_factory=list)
    bibliography: list[BibliographyEntryDTO] = field(default_factory=list)
    related_assets: list[RelatedAssetDTO] = field(default_factory=list)


@dataclass(frozen=True)
class InmaterialDetailsDTO:
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
    typologies: list[TypologyInfoDTO] = field(default_factory=list)
    images: list[ImageInfoDTO] = field(default_factory=list)
    bibliography: list[BibliographyEntryDTO] = field(default_factory=list)
    related_assets: list[RelatedAssetDTO] = field(default_factory=list)


@dataclass(frozen=True)
class PaisajeDetailsDTO:
    type: str = "paisaje"
    pdf_url: str | None = None
    search_terms: list[str] = field(default_factory=list)


DetailsDTO = (
    InmuebleDetailsDTO
    | MuebleDetailsDTO
    | InmaterialDetailsDTO
    | PaisajeDetailsDTO
)


@dataclass(frozen=True)
class HeritageAssetDTO:
    id: str
    heritage_type: str
    denomination: str | None = None
    province: str | None = None
    municipality: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    image_url: str | None = None
    image_ids: list[str] = field(default_factory=list)
    protection: str | None = None
    details: DetailsDTO | None = None


@dataclass(frozen=True)
class HeritageAssetListDTO:
    items: list[HeritageAssetDTO]
    total: int
    limit: int
    offset: int
