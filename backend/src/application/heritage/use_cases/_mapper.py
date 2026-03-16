"""Maps domain entities → application DTOs for heritage assets."""

from src.application.heritage.dto.heritage_dto import (
    BibliographyEntryDTO,
    DetailsDTO,
    HeritageAssetDTO,
    ImageInfoDTO,
    InmaterialDetailsDTO,
    InmuebleDetailsDTO,
    MuebleDetailsDTO,
    PaisajeDetailsDTO,
    RelatedAssetDTO,
    TypologyInfoDTO,
)
from src.domain.heritage.entities.heritage_asset import HeritageAsset
from src.domain.heritage.value_objects.raw_data import (
    InmaterialRawData,
    InmuebleRawData,
    MuebleRawData,
    PaisajeRawData,
)


def _map_images(images) -> list[ImageInfoDTO]:
    return [
        ImageInfoDTO(
            id=img.id, title=img.title, author=img.author,
            date=img.date, url=img.url,
        )
        for img in images
    ]


def _map_bibliography(bib) -> list[BibliographyEntryDTO]:
    return [
        BibliographyEntryDTO(
            title=b.title, author=b.author, publisher=b.publisher,
            year=b.year, isbn=b.isbn, pages=b.pages, location=b.location,
        )
        for b in bib
    ]


def _map_typologies(typos) -> list[TypologyInfoDTO]:
    return [
        TypologyInfoDTO(
            typology=t.typology, style=t.style, period=t.period,
            chrono_start=t.chrono_start, chrono_end=t.chrono_end,
        )
        for t in typos
    ]


def _map_related(related) -> list[RelatedAssetDTO]:
    return [
        RelatedAssetDTO(
            code=r.code, denomination=r.denomination,
            relation_type=r.relation_type,
        )
        for r in related
    ]


def _map_details(details) -> DetailsDTO | None:
    if details is None:
        return None

    if isinstance(details, InmuebleRawData):
        return InmuebleDetailsDTO(
            code=details.code,
            other_denominations=details.other_denominations,
            characterisation=details.characterisation,
            postal_address=details.postal_address,
            historical_data=details.historical_data,
            description=details.description,
            protection=details.protection,
            typologies=_map_typologies(details.typologies),
            images=_map_images(details.images),
            bibliography=_map_bibliography(details.bibliography),
            related_assets=_map_related(details.related_assets),
            historical_periods=details.historical_periods,
        )
    elif isinstance(details, MuebleRawData):
        return MuebleDetailsDTO(
            code=details.code,
            other_denominations=details.other_denominations,
            characterisation=details.characterisation,
            measurements=details.measurements,
            chronology=details.chronology,
            description=details.description,
            protection=details.protection,
            typologies=_map_typologies(details.typologies),
            images=_map_images(details.images),
            bibliography=_map_bibliography(details.bibliography),
            related_assets=_map_related(details.related_assets),
        )
    elif isinstance(details, InmaterialRawData):
        return InmaterialDetailsDTO(
            code=details.code,
            other_denominations=details.other_denominations,
            scope=details.scope,
            framework_activities=details.framework_activities,
            activity_dates=details.activity_dates,
            periodicity=details.periodicity,
            typologies_text=details.typologies_text,
            district=details.district,
            local_entity=details.local_entity,
            description=details.description,
            development=details.development,
            spatial_description=details.spatial_description,
            agents_description=details.agents_description,
            evolution=details.evolution,
            origins=details.origins,
            preparations=details.preparations,
            clothing=details.clothing,
            instruments=details.instruments,
            transmission_mode=details.transmission_mode,
            transformations=details.transformations,
            protection=details.protection,
            typologies=_map_typologies(details.typologies),
            images=_map_images(details.images),
            bibliography=_map_bibliography(details.bibliography),
            related_assets=_map_related(details.related_assets),
        )
    elif isinstance(details, PaisajeRawData):
        return PaisajeDetailsDTO(
            pdf_url=details.pdf_url,
            search_terms=details.search_terms,
        )
    return None


def entity_to_dto(entity: HeritageAsset) -> HeritageAssetDTO:
    return HeritageAssetDTO(
        id=entity.id,
        heritage_type=entity.heritage_type,
        denomination=entity.denomination,
        province=entity.province,
        municipality=entity.municipality,
        latitude=entity.latitude,
        longitude=entity.longitude,
        image_url=entity.image_url,
        image_ids=entity.image_ids,
        protection=entity.protection,
        details=_map_details(entity.details),
    )
