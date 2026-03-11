from enum import StrEnum


class HeritageTypeFilter(StrEnum):
    PAISAJE_CULTURAL = "paisaje_cultural"
    PATRIMONIO_INMATERIAL = "patrimonio_inmaterial"
    PATRIMONIO_INMUEBLE = "patrimonio_inmueble"
    PATRIMONIO_MUEBLE = "patrimonio_mueble"
    ALL = "ALL"
