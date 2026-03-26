# Analisis exploratorio -- DBpedia en API IAPH (endpoint enriquecido)

**Fecha:** 2026-03-26
**Fuente:** API IAPH endpoint enriquecido (`https://guiadigital.iaph.es/api/1.0/bien/{tipo}/enriquecido/{id}`)
**Muestra:** 500 assets (estratificada proporcional desde `heritage_assets`)
**Script:** `scripts/eda_dbpedia_lookup.py`

---

## 1. Contexto

La API IAPH expone dos endpoints por activo:

| Endpoint | Formato | DBpedia |
|----------|---------|---------|
| `/busqueda/{tipo}/rows=...` (Solr) | JSON plano | **No** |
| `/bien/{tipo}/enriquecido/{id}` (detalle) | JSON-LD con `@id`, `@type`, `prov:wasAssociatedWith` | **Si** |

La tabla `heritage_assets.raw_data` almacena datos del endpoint Solr (plano), que **no contiene URIs DBpedia**. Este EDA consulta el endpoint enriquecido para evaluar la disponibilidad y utilidad de los enlaces DBpedia.

---

## 2. Disponibilidad del endpoint enriquecido

No todos los assets tienen respuesta enriquecida disponible. El servicio interno de enriquecimiento (`contentenrichment-webservice`) falla (HTTP 500) para una parte significativa de los assets.

| Tipo | Consultados | Con respuesta | Con DBpedia | Sin respuesta (500) |
|------|--------:|--------:|--------:|--------:|
| **inmueble** | 81 | 58 (71,6%) | 58 (71,6%) | 23 (28,4%) |
| **mueble** | 296 | 296 (100%) | 0 (0%) | 0 (0%) |
| **inmaterial** | 5 | 5 (100%) | 0 (0%) | 0 (0%) |
| **paisaje** | 118 | 118 (100%) | 0 (0%) | 0 (0%) |

> **Solo patrimonio inmueble contiene URIs DBpedia.** Mueble, inmaterial y paisaje devuelven JSON valido pero sin ningun enlace a DBpedia. El ~28% de inmueble falla con 500 (servicio de enriquecimiento no disponible para esos registros).

---

## 3. Tipos de URIs DBpedia encontradas

Se extrajeron **628 URIs DBpedia** de 58 assets de inmueble. Tras filtrar prefijos JSON-LD (`context_ns`) y duplicados en fotos (`foto_geo`), quedan **512 URIs utiles**.

### 3.1 Categorizacion por JSON path

Las URIs se categorizaron segun su ubicacion en la estructura JSON-LD:

| Categoria | Ocurrencias | URIs unicas | Que referencia | Ejemplo |
|-----------|--------:|--------:|----------------|---------|
| `tipologia_dbpedia` | 148 | 49 | Conceptos tipologicos via `prov:wasAssociatedWith` | `es.dbpedia.org/resource/Asentamiento` |
| `provincia` | 116 | 8 | Provincia del bien | `es.dbpedia.org/resource/Jaén` |
| `entidad_descripcion` | 113 | 38 | Entidades NER en texto descriptivo | `es.dbpedia.org/resource/Iglesia` |
| `municipio` | 112 | 43 | Municipio del bien | `es.dbpedia.org/resource/Linares_(Salas)` |
| `foto_geo` | 116 | 46 | Geo repetida en metadatos de foto | (duplicados de municipio/provincia) |
| `asociacion_dbpedia` | 12 | 2 | Roles profesionales | `es.dbpedia.org/resource/Arquitecto` |
| `etnia_dbpedia` | 11 | 5 | Grupos culturales/etnicos | `es.dbpedia.org/resource/Iberos` |
| `context_ns` | 174 | 3 | Prefijos de namespace JSON-LD | `dbpedia.org/ontology/` |

### 3.2 JSON paths donde aparecen las URIs

| JSON path (generalizado) | Ocurrencias | Categoria |
|--------------------------|--------:|-----------|
| `$.municipio.@id` | 58 | municipio |
| `$.provincia.@id` | 58 | provincia |
| `$.identifica.municipio.@id` | 54 | municipio |
| `$.identifica.provincia.@id` | 58 | provincia |
| `$.tipologiaList.tipologia[*].periodos.prov:wasAssociatedWith[*].@id` | 72 | tipologia_dbpedia |
| `$.tipologiaList.tipologia[*].den_tipologia.prov:wasAssociatedWith[*].@id` | 65 | tipologia_dbpedia |
| `$.tipologiaList.tipologia[*].den_etnia.prov:wasAssociatedWith[*].@id` | 11 | etnia_dbpedia |
| `$.identifica.descripcion.Resources[*].@URI` | ~56 | entidad_descripcion |
| `$.clob.descripcion.Resources[*].@URI` | ~57 | entidad_descripcion |
| `$.fotoList.foto.municipio.@id` / `$.fotoList.foto.provincia.@id` | 116 | foto_geo |
| `$.context.dbo` / `$.context.esdbpr` / `$.context.esdbpp` | 174 | context_ns |

---

## 4. URIs DBpedia mas frecuentes

### 4.1 Top-20 (excluyendo context_ns y foto_geo)

| URI | Ocurrencias | Categoria |
|-----|--------:|-----------|
| `Provincia_de_Sevilla` | 42 | municipio |
| `Iglesia` | 20 | entidad_descripcion |
| `Época_romana` | 20 | tipologia_dbpedia |
| `Huelva` | 20 | provincia |
| `Jaén` | 20 | provincia |
| `Asentamiento` | 17 | tipologia_dbpedia |
| `Edad_Contemporánea` | 16 | tipologia_dbpedia |
| `Málaga` | 16 | provincia |
| `Edad_Moderna` | 13 | tipologia_dbpedia |
| `Arquitecto` | 11 | asociacion_dbpedia |
| `Provincia_de_Córdoba_(España)` | 10 | provincia |
| `Provincia_de_Almería` | 10 | provincia |
| `Granada` | 10 | provincia |
| `Alto_Imperio_romano` | 9 | tipologia_dbpedia |
| `Provincia_de_Cádiz` | 8 | provincia |
| `Carmona_(Cantabria)` | 8 | municipio |
| `Edad_Media` | 8 | tipologia_dbpedia |
| `Cástulo` | 6 | entidad_descripcion |
| `Linares_(Salas)` | 6 | municipio |
| `Cártama` | 6 | municipio |

### 4.2 Entidades en descripcion (NER) -- Top-15

Estas URIs provienen de campos `Resources[*].@URI` dentro de textos descriptivos. Representan entidades detectadas automaticamente (NER) en la descripcion del bien:

| Entidad | Ocurrencias |
|---------|--------:|
| Iglesia | 20 |
| Castulo | 6 |
| Cristo | 4 |
| Coria | 4 |
| 2005 | 4 |
| Derby | 4 |
| Guadalhorce | 4 |
| Odiel | 4 |
| Sevilla | 4 |
| Palisandro | 4 |
| Salpensa | 2 |
| Alto Imperio romano | 2 |
| Paterna | 2 |
| Fontanilla | 2 |
| Jorge Bonsor | 2 |

> Las entidades NER son mayoritariamente **genericas** (Iglesia, Cristo) o **toponimos cercanos** (Castulo, Coria, Guadalhorce). Ninguna referencia al propio activo patrimonial como concepto en DBpedia.

---

## 5. Activos patrimoniales y DBpedia propia

**No se encontro ningun asset cuyo propio concepto tenga entrada en DBpedia** a traves de este endpoint.

Las URIs DBpedia observadas se clasifican exclusivamente en:

| Tipo de referencia | Descripcion | Ejemplo |
|--------------------|-------------|---------|
| **Geografica** | Municipio y provincia del bien | `Linares_(Salas)`, `Jaén` |
| **Tipologica** | Tipo de bien via ontologia IAPH → DBpedia | `Asentamiento`, `Ciudad` |
| **Temporal** | Periodo historico | `Época_romana`, `Alto_Imperio_romano` |
| **Cultural** | Grupo etnico/cultural | `Iberos`, `Cultura_de_La_Tène` |
| **NER textual** | Entidades detectadas en descripciones | `Iglesia`, `Cástulo`, `Jorge_Bonsor` |
| **Profesional** | Roles asociados | `Arquitecto` |

Todas son **entidades auxiliares** que contextualizan el bien, no lo identifican en DBpedia.

---

## 6. Calidad de las URIs

### Problemas detectados

| Problema | Ejemplo | Impacto |
|----------|---------|---------|
| **Desambiguacion incorrecta** | `Linares_(Salas)` en vez de `Linares_(Jaén)` | El municipio apunta a la localidad asturiana, no la jiennense |
| **Desambiguacion incorrecta** | `Carmona_(Cantabria)` en vez de `Carmona_(Sevilla)` | Idem, municipio equivocado |
| **NER ruidoso** | `2005`, `Derby`, `Palisandro` detectados como entidades | Falsos positivos del NER |
| **URIs vacias** | `prov:wasAssociatedWith[{"@id":""}]` | Arrays con URIs vacias (sin enlace) |
| **Duplicacion** | Misma URI municipio/provincia en `$`, `$.identifica` y `$.fotoList` | Triple redundancia |

> La desambiguacion geografica es un problema significativo: varios municipios andaluces apuntan a homonimos en otras comunidades autonomas.

---

## 7. Conclusiones

### 7.1 Valor de DBpedia en el corpus IAPH

1. **Solo inmueble tiene enriquecimiento DBpedia** (71,6% de los consultados). Mueble, inmaterial y paisaje no aportan nada.

2. **No existen enlaces DBpedia al propio activo patrimonial.** Los bienes del IAPH (yacimientos arqueologicos, cortijos, iglesias concretas) no tienen correspondencia en DBpedia/Wikipedia como entidades individuales.

3. **Las URIs son auxiliares** (geografia, tipologia, periodos, etnias). Util para enriquecimiento contextual pero no para identificacion del bien.

4. **Problemas de calidad**: desambiguacion incorrecta de municipios, NER ruidoso, URIs vacias.

### 7.2 Posibles usos

| Uso | Viabilidad | Valor |
|-----|-----------|-------|
| Enlazar activo → articulo Wikipedia | **No viable** | No existen esos enlaces |
| Enriquecer contexto geografico (poblacion, coordenadas) | **Viable con cautela** | Requiere corregir desambiguacion |
| Mapear tipologias a ontologias estandar | **Viable** | 49 conceptos tipologicos enlazados |
| Enriquecer periodos historicos con descripciones | **Viable** | Periodos ya enlazados correctamente |
| Ampliar busqueda semantica via DBpedia | **Bajo valor** | Las entidades NER son ruidosas |

### 7.3 Recomendacion

**No invertir en integracion DBpedia para el RAG actual.** Los enlaces existentes son auxiliares y con problemas de calidad. El enriquecimiento mas valioso (tipologias y periodos) ya esta disponible directamente en los datos IAPH sin necesidad de consultar DBpedia. Si se necesita enriquecimiento geografico (coordenadas de municipios), es preferible usar un geocodificador dedicado (Nominatim) en vez de depender de las URIs DBpedia mal desambiguadas.

---

## Apendice: estructura JSON-LD del endpoint enriquecido

Ejemplo simplificado de la respuesta para un inmueble con DBpedia:

```json
{
  "provincia_s": "Jaén",
  "municipio": {
    "@id": "http://es.dbpedia.org/resource/Linares_(Salas)",
    "@type": "schema:City"
  },
  "provincia": {
    "@id": "http://es.dbpedia.org/resource/Jaén",
    "@type": "schema:State"
  },
  "tipologiaList": {
    "tipologia": [{
      "den_tipologia": {
        "@id": "iaph:e-Asentamientos",
        "rdfs:label": "Asentamientos",
        "prov:wasAssociatedWith": [
          {"@id": "http://es.dbpedia.org/resource/Asentamiento"},
          {"@id": ""}
        ]
      },
      "periodos": {
        "@id": "iaph:e-Alto_imperio_romano",
        "rdfs:label": "Alto imperio romano",
        "prov:wasAssociatedWith": [
          {"@id": "http://es.dbpedia.org/resource/Alto_Imperio_romano"}
        ]
      }
    }]
  },
  "identifica": {
    "descripcion": {
      "@text": "Restos de un asentamiento romano...",
      "Resources": [
        {"@URI": "http://es.dbpedia.org/resource/Cástulo", "@surfaceForm": "Cástulo"}
      ]
    }
  },
  "context": {
    "dbo": "http://dbpedia.org/ontology/",
    "esdbpr": "http://es.dbpedia.org/resource/",
    "esdbpp": "http://es.dbpedia.org/property/"
  }
}
```

---

## Ficheros generados

| Fichero | Descripcion |
|---------|-------------|
| `scripts/eda_dbpedia_lookup.py` | Script de consulta al endpoint enriquecido + EDA |

> Los resultados generados (CSV, checkpoint, muestras JSON) se guardan en `scripts/results/` (gitignored).
