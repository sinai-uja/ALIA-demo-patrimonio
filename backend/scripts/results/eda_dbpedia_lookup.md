# EDA: DBpedia en endpoint enriquecido IAPH

**Fecha**: 2026-03-26 12:35
**Assets consultados**: 500 / 500

## 1. Resumen

- Assets con al menos 1 URI DBpedia: **58** (11.6%)
- Total URIs DBpedia encontradas: **802**
- Assets no disponibles (500 — enrichment falla): 23
- Assets no encontrados (404): 118
- Errores: 0

## 2. Assets con DBpedia por heritage_type

| heritage_type | Consultados | Con DBpedia | % | URIs totales |
|---|---|---|---|---|
| inmaterial | 5 | 0 | 0.0% | 0 |
| inmueble | 81 | 58 | 71.6% | 802 |
| mueble | 296 | 0 | 0.0% | 0 |
| paisaje | 118 | 0 | 0.0% | 0 |

## 3. Desglose por categoría semántica

| Categoría | Ocurrencias | URIs únicas | Ejemplo |
|---|---|---|---|
| context_ns | 174 | 3 | `http://es.dbpedia.org/resource/` |
| tipologia_dbpedia | 148 | 49 | `http://es.dbpedia.org/resource/Arquitectura_neobizantina` |
| provincia | 116 | 8 | `http://es.dbpedia.org/resource/Provincia_de_Córdoba_(España)` |
| foto_geo | 116 | 46 | `http://es.dbpedia.org/resource/Cala_(Huelva)` |
| entidad_descripcion | 113 | 38 | `http://es.dbpedia.org/resource/Casas_Altas` |
| municipio | 112 | 43 | `http://es.dbpedia.org/resource/Cala_(Huelva)` |
| asociacion_dbpedia | 12 | 2 | `http://es.dbpedia.org/resource/Aparejador` |
| etnia_dbpedia | 11 | 5 | `http://es.dbpedia.org/resource/Pueblo_visigodo` |

## 4. Top-30 URIs DBpedia más frecuentes

| URI | Ocurrencias | Categoría |
|---|---|---|
| `http://es.dbpedia.org/resource/Provincia_de_Sevilla` | 63 | municipio |
| `http://dbpedia.org/ontology/` | 58 | context_ns |
| `http://es.dbpedia.org/property/` | 58 | context_ns |
| `http://es.dbpedia.org/resource/` | 58 | context_ns |
| `http://es.dbpedia.org/resource/Jaén` | 30 | provincia |
| `http://es.dbpedia.org/resource/Huelva` | 29 | provincia |
| `http://es.dbpedia.org/resource/Málaga` | 24 | provincia |
| `http://es.dbpedia.org/resource/Época_romana` | 20 | tipologia_dbpedia |
| `http://es.dbpedia.org/resource/Iglesia` | 20 | entidad_descripcion |
| `http://es.dbpedia.org/resource/Asentamiento` | 17 | tipologia_dbpedia |
| `http://es.dbpedia.org/resource/Edad_Contemporánea` | 16 | tipologia_dbpedia |
| `http://es.dbpedia.org/resource/Granada` | 16 | provincia |
| `http://es.dbpedia.org/resource/Provincia_de_Córdoba_(España)` | 15 | provincia |
| `http://es.dbpedia.org/resource/Provincia_de_Almería` | 15 | provincia |
| `http://es.dbpedia.org/resource/Edad_Moderna` | 13 | tipologia_dbpedia |
| `http://es.dbpedia.org/resource/Provincia_de_Cádiz` | 12 | provincia |
| `http://es.dbpedia.org/resource/Carmona_(Cantabria)` | 12 | municipio |
| `http://es.dbpedia.org/resource/Arquitecto` | 11 | asociacion_dbpedia |
| `http://es.dbpedia.org/resource/Alto_Imperio_romano` | 9 | tipologia_dbpedia |
| `http://es.dbpedia.org/resource/Linares_(Salas)` | 9 | municipio |
| `http://es.dbpedia.org/resource/Edad_Media` | 8 | tipologia_dbpedia |
| `http://es.dbpedia.org/resource/Cártama` | 8 | municipio |
| `http://es.dbpedia.org/resource/Cástulo` | 6 | entidad_descripcion |
| `http://es.dbpedia.org/resource/Utrera` | 6 | municipio |
| `http://es.dbpedia.org/resource/Lebrija_(Santander)` | 6 | municipio |
| `http://es.dbpedia.org/resource/Dos_Hermanas` | 6 | municipio |
| `http://es.dbpedia.org/resource/Dólar_(Granada)` | 6 | municipio |
| `http://es.dbpedia.org/resource/Iberos` | 5 | etnia_dbpedia |
| `http://es.dbpedia.org/resource/Cultura_de_La_Tène` | 5 | tipologia_dbpedia |
| `http://es.dbpedia.org/resource/Bajo_Imperio_romano` | 4 | tipologia_dbpedia |

## 5. Assets con URI DBpedia del propio activo

**4 assets** con posibles URIs DBpedia propias:

- **Facultad de Biología** (`217527`, inmueble)
  - `$.agenteList.agente[0].tipo_agen.prov:wasAssociatedWith[0].@id` → `http://es.dbpedia.org/resource/Arquitecto`
  - `$.agenteList.agente[1].tipo_agen.prov:wasAssociatedWith[0].@id` → `http://es.dbpedia.org/resource/Arquitecto`
  - `$.agenteList.agente[2].tipo_agen.prov:wasAssociatedWith[0].@id` → `http://es.dbpedia.org/resource/Arquitecto`
  - `$.agenteList.agente[3].tipo_agen.prov:wasAssociatedWith[0].@id` → `http://es.dbpedia.org/resource/Arquitecto`
- **Centro de Empresas** (`8139`, inmueble)
  - `$.agenteList.agente[0].tipo_agen.prov:wasAssociatedWith[0].@id` → `http://es.dbpedia.org/resource/Arquitecto`
  - `$.agenteList.agente[2].tipo_agen.prov:wasAssociatedWith[0].@id` → `http://es.dbpedia.org/resource/Aparejador`
- **Antiguo Hotel Alameda** (`20782`, inmueble)
  - `$.agenteList.agente[0].tipo_agen.prov:wasAssociatedWith[0].@id` → `http://es.dbpedia.org/resource/Arquitecto`
  - `$.agenteList.agente[1].tipo_agen.prov:wasAssociatedWith[0].@id` → `http://es.dbpedia.org/resource/Arquitecto`
- **Jardines Edificio 13. Francisco José de Caldas.** (`245443`, inmueble)
  - `$.agenteList.agente[0].tipo_agen.prov:wasAssociatedWith[0].@id` → `http://es.dbpedia.org/resource/Arquitecto`
  - `$.agenteList.agente[1].tipo_agen.prov:wasAssociatedWith[0].@id` → `http://es.dbpedia.org/resource/Arquitecto`
  - `$.agenteList.agente[2].tipo_agen.prov:wasAssociatedWith[0].@id` → `http://es.dbpedia.org/resource/Arquitecto`
  - `$.agenteList.agente[3].tipo_agen.prov:wasAssociatedWith[0].@id` → `http://es.dbpedia.org/resource/Arquitecto`

## 6. JSON paths donde aparecen URIs DBpedia

| JSON path (generalizado) | Ocurrencias |
|---|---|
| `$.tipologiaList.tipologia[*].periodos.prov:wasAssociatedWith[*].@id` | 62 |
| `$.provincia.@id` | 58 |
| `$.identifica.provincia.@id` | 58 |
| `$.context.dbo` | 58 |
| `$.context.esdbpp` | 58 |
| `$.context.esdbpr` | 58 |
| `$.clob.descripcion.Resources[*].@URI` | 58 |
| `$.fotoList.foto.provincia.@id` | 57 |
| `$.identifica.municipio.@id` | 56 |
| `$.municipio.@id` | 56 |
| `$.fotoList.foto.municipio.@id` | 55 |
| `$.identifica.descripcion.Resources[*].@URI` | 55 |
| `$.tipologiaList.tipologia.periodos.prov:wasAssociatedWith[*].@id` | 29 |
| `$.tipologiaList.tipologia[*].den_tipologia.prov:wasAssociatedWith[*].@id` | 27 |
| `$.tipologiaList.tipologia.den_tipologia.prov:wasAssociatedWith[*].@id` | 15 |
| `$.agenteList.agente[*].tipo_agen.prov:wasAssociatedWith[*].@id` | 12 |
| `$.tipologiaList.tipologia[*].den_etnia.prov:wasAssociatedWith[*].@id` | 8 |
| `$.tipologiaList.tipologia[*].den_estilo.prov:wasAssociatedWith[*].@id` | 6 |
| `$.tipologiaList.tipologia[*].denom_acti.prov:wasAssociatedWith[*].@id` | 4 |
| `$.tipologiaList.tipologia.denom_acti.prov:wasAssociatedWith[*].@id` | 3 |
| `$.tipologiaList.tipologia.den_etnia.prov:wasAssociatedWith[*].@id` | 3 |
| `$.tipologiaList.tipologia.den_estilo.prov:wasAssociatedWith[*].@id` | 2 |
| `$.fotoList.foto[*].municipio.@id` | 2 |
| `$.fotoList.foto[*].provincia.@id` | 2 |

## 7. Muestras de respuesta JSON-LD

### inmaterial_193465.json

```json
{
  "imagen": {
    "response": null
  }
}
```

### inmaterial_193751.json

```json
{
  "imagen": {
    "response": null
  }
}
```

### inmaterial_216430.json

```json
{
  "imagen": {
    "response": null
  }
}
```


## 8. Conclusión

El **11.6%** de los activos consultados (58/500) incluye al menos una URI DBpedia en su respuesta enriquecida.

### Tipos de referencia:

- **4 assets** tienen URIs DBpedia que podrían referenciar al propio activo patrimonial (categorías: identificación, asociación, derivación, otro)
- Las URIs DBpedia más comunes son de **entidades auxiliares**: municipios, provincias, tipologías y periodos históricos

### Valor para el corpus:

1. **Enriquecimiento geográfico**: URIs de municipios y provincias permiten enlazar con datos geográficos de DBpedia (coordenadas, población, etc.)
2. **Enriquecimiento tipológico**: URIs de tipologías permiten mapear categorías IAPH a conceptos estándar de la ontología DBpedia
3. **Enriquecimiento temporal**: URIs de periodos históricos vinculan a la descripción en DBpedia del periodo
4. **Enlace directo**: 4 activos tienen referencia DBpedia propia, permitiendo acceder a información complementaria en Wikipedia/DBpedia
