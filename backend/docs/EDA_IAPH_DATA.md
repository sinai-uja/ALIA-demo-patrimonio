# Analisis exploratorio de datos -- Datos API IAPH (`heritage_assets`)

**Fecha:** 2026-03-16
**Fuente:** API REST IAPH (`https://guiadigital.iaph.es/api/1.0/`)
**Tabla:** `heritage_assets` (528 MB, 139.343 registros)

---

## 1. Vision general

La tabla `heritage_assets` almacena datos estructurados obtenidos de la API publica del IAPH. Cada registro representa un bien patrimonial catalogado en Andalucia, con una columna JSONB `raw_data` que preserva la respuesta completa de la API.

| Tipo | Total | % |
|------|------:|--:|
| **Patrimonio Mueble** (obras de arte, objetos) | 107.732 | 77,3% |
| **Patrimonio Inmueble** (edificios, yacimientos) | 29.569 | 21,2% |
| **Patrimonio Inmaterial** (tradiciones, oficios) | 1.924 | 1,4% |
| **Paisaje Cultural** (paisajes culturales) | 118 | 0,1% |
| **TOTAL** | **139.343** | |

> El corpus esta dominado abrumadoramente por **patrimonio mueble** (77%). El patrimonio inmaterial y los paisajes culturales son comparativamente escasos.

---

## 2. Completitud de campos estructurados

Columnas extraidas de la API al esquema relacional:

| Tipo | Total | denominacion | provincia | municipio | lat/lon | imagen | proteccion |
|------|------:|:-----------:|:--------:|:------------:|:-------:|:---------:|:----------:|
| mueble | 107.732 | 99,9% | 99,9% | 99,9% | **0%** | 66,1% | 99,9% |
| inmueble | 29.569 | 100% | 100% | 100% | **16,3%** | 46,3% | 100% |
| inmaterial | 1.924 | 100% | 100% | 100% | **0%** | 94,1% | 100% |
| paisaje | 118 | 100% | 100% | **0%** | **0%** | 100% | **0%** |

### Carencias principales

- **Geolocalizacion (lat/lon):** solo **4.806 bienes** (3,4%) tienen coordenadas, todos de tipo `inmueble`. Mueble, inmaterial y paisaje tienen cero coordenadas. Esto limita severamente las funciones basadas en mapa y la generacion de rutas.
- **Imagenes:** 86.821 bienes (62%) tienen al menos una imagen. Mejor cobertura en inmaterial (94%) y paisaje (100%); peor en inmueble (46%).
- **Paisaje es el tipo menos enriquecido:** sin municipio, sin coordenadas, sin estado de proteccion, y solo 8 claves JSONB frente a 60-110 en otros tipos.
- **1 registro de mueble** tiene denominacion/provincia/municipio NULL (probablemente un registro corrupto de la API).

---

## 3. Riqueza del JSONB `raw_data`

Cada tipo de patrimonio tiene un esquema interno muy diferente. El numero de claves JSONB por registro es un indicador de profundidad de datos:

| Tipo | Media claves | Min | Max |
|------|:--------:|:---:|:---:|
| inmaterial | 106 | 60 | 134 |
| inmueble | 74 | 29 | 110 |
| mueble | 63 | 2 | 114 |
| paisaje | 8 | 8 | 8 |

> Inmaterial es el tipo mas ricamente descrito (media 106 claves). Algunos registros de mueble tienen tan solo 2 claves (esencialmente vacios).

---

## 4. Patrimonio Inmueble -- analisis detallado (29.569 registros)

### 4.1 Campos principales (100% cobertura)

Todos los registros tienen: `denominacion`, `provincia`, `municipio`, `descripcion`, `dat_historico`, `dir_postal`, `caracterizacion`, `proteccion`, `codigo`, `otr_denom`, `estado`.

> Es el tipo mas completo y uniforme del dataset.

### 4.2 Caracterizacion

| Caracterizacion | Registros | % |
|-----------------|------:|--:|
| Arqueologica | 16.421 | 55,5% |
| Arquitectonica | 5.965 | 20,2% |
| Etnologica | 3.405 | 11,5% |
| Arquitectonica + Etnologica | 2.176 | 7,4% |
| Arqueologica + Arquitectonica | 1.249 | 4,2% |
| Otros / vacio | 353 | 1,2% |

> Mas de la mitad del patrimonio inmueble es arqueologico. Los sitios arquitectonicos son el segundo grupo mas grande.

### 4.3 Tipologias (29.126 registros -- 98,5%)

| Principales tipologias | Registros |
|------------------------|------:|
| Asentamientos | 2.151 |
| Villae (villas romanas) | 1.452 |
| (vacio) | 809 |
| Sitios con representaciones rupestres | 624 |
| Construcciones funerarias | 582 |
| Puentes | 560 |
| Restos de artefactos | 549 |
| Cortijos | 458 |
| Dolmenes | 448 |
| Poblados | 437 |
| Iglesias | 420 |
| Ermitas | 389 |

> Nota: 809 registros tienen tipologia en blanco (`[" "]`), y 687 tienen valores duplicados (`["Asentamientos", "Asentamientos"]`).

### 4.4 Periodos historicos (29.126 registros)

| Principales periodos | Registros |
|---------------------|------:|
| Edad Contemporanea | 5.104 |
| Epoca romana | 3.689 |
| (vacio) | 2.938 |
| Edad Moderna | 1.858 |
| Edad Media | 1.505 |
| Prehistoria reciente | 1.102 |
| Edad del cobre | 923 |
| Alto imperio romano | 571 |

> El 10% de los valores de periodo son blancos (`[" "]`). Muchos registros tienen arrays multiperiodo indicando bienes que abarcan varias epocas.

### 4.5 Estilos (29.126 registros)

| Estilo | Registros |
|--------|------:|
| **(vacio)** | **18.436** |
| (2+ valores vacios) | 8.838 |
| Barroco | 243 |
| Racionalista | 129 |
| Mudejar | 121 |
| Renacimiento | 82 |
| Neoclasicismo | 66 |

> **El 94% de los registros de inmueble no tienen informacion de estilo.** El campo de estilo esta esencialmente sin rellenar -- solo ~1.700 registros tienen un valor significativo.

### 4.6 Enriquecimientos adicionales

| Campo | Registros | Cobertura |
|-------|--------:|--------:|
| Fotografias (foto.id_smv) | 29.560 | 99,9% |
| Tipografia | 29.126 | 98,5% |
| Texto de descripcion | 28.144 | 95,2% |
| Cronologia inicio (crono_ini) | 23.840 | 80,6% |
| Cronologia fin (crono_fin) | 25.909 | 87,6% |
| Bibliografia | 13.357 | 45,2% |
| Detalles de proteccion | 5.671 | 19,2% |

---

## 5. Patrimonio Mueble -- analisis detallado (107.732 registros)

### 5.1 Campos principales

| Campo | Presentes | Cobertura |
|-------|--------:|--------:|
| denominacion | 107.731 | >99,9% |
| provincia / municipio | 107.731 | >99,9% |
| cronologia (texto) | 107.731 | >99,9% |
| datos historicos | 107.731 | >99,9% |
| descripcion (texto) | 92.842 | **86,2%** |
| tipologia | 93.148 | 86,4% |
| materiales | 92.511 | 85,8% |
| tecnicas | 92.566 | 85,9% |
| estilos | 77.852 | 72,2% |
| iconografia | 60.859 | 56,5% |
| bibliografia | 33.385 | 31,0% |
| fotografias (foto.id_smv) | 8.809 | 8,2% |

> **14.890 registros de mueble (13,8%) no tienen texto de descripcion.** La bibliografia solo esta disponible para el 31% de los registros.

### 5.2 Caracterizacion

| Caracterizacion | Registros | % |
|-----------------|------:|--:|
| Etnologica | 102.395 | 95,0% |
| Sin Caracterizacion | 5.102 | 4,7% |
| Arqueologica | 131 | 0,1% |
| Otros | 104 | 0,1% |

> El 95% del patrimonio mueble esta clasificado como etnologico. 5.102 registros (4,7%) no tienen caracterizacion.

### 5.3 Principales tipologias

| Tipologia | Registros |
|-----------|------:|
| Pinturas de caballete | 10.805 |
| Esculturas de bulto redondo | 5.519 |
| Pinturas | 4.195 |
| Fotografias | 2.928 |
| Relieves | 2.461 |
| Pinturas murales | 2.407 |
| Retablos | 2.315 |
| Calices | 1.380 |
| Azulejos | 1.103 |
| Altorrelieves | 1.102 |

### 5.4 Principales materiales

| Material | Registros |
|----------|------:|
| Plata | 6.788 |
| Lienzo + pigmento al aceite | 6.577 |
| Madera + pigmento | 4.406 |
| Pigmento al aceite | 3.995 |
| Madera | 2.813 |
| Marmol | 2.498 |
| Madera + pan de oro + pigmento | 2.277 |

### 5.5 Principales estilos

| Estilo | Registros |
|--------|------:|
| Barroco | 41.682 |
| Neobarroco | 5.201 |
| Neoclasicismo | 5.087 |
| Renacimiento | 4.074 |
| Rococo | 3.232 |
| Manierismo | 3.205 |
| Arte contemporaneo | 2.625 |
| Eclecticista | 1.544 |
| Historicista | 1.042 |

> A diferencia de inmueble, mueble tiene datos de estilo ricos. **El Barroco domina abrumadoramente** con 41K registros (53% de los que tienen estilo).

---

## 6. Patrimonio Inmaterial -- analisis detallado (1.924 registros)

### 6.1 Campos principales (100% cobertura, 100% no vacios)

Los 1.924 registros tienen completamente rellenos: `descripcion`, `desarrollo`, `origenes`, `transformaciones`, `instrumentos`, `tipologias`, `periodicidad`, `fechasact`.

> Es el tipo mas uniformemente completo -- todos los registros tienen todos los campos narrativos rellenos.

### 6.2 Principales tipologias

| Tipologia | Registros |
|-----------|------:|
| Procesion civico-religiosa | 150 |
| Produccion de alimentos | 145 |
| Semana Santa | 122 |
| Romeria | 111 |
| (vacio) | 78 |
| Actividad festivo-ceremonial | 60 |
| Reposteria | 55 |
| Feria | 54 |
| Carnavales | 34 |
| Canciones | 34 |
| Alfareria | 32 |
| Vinicultura | 32 |

> Las procesiones religiosas, la produccion de alimentos y la Semana Santa son los tipos de patrimonio inmaterial mas catalogados.

### 6.3 Proteccion

Solo **75 de 1.924** (3,9%) bienes inmateriales tienen proteccion formal.

---

## 7. Paisaje Cultural -- analisis detallado (118 registros)

El tipo mas simple con solo 8 claves JSONB: `id`, `tipo_contenido`, `provincia`, `provincia_smv`, `titulo`, `busqueda_generica`, `pdf_url`, `imagen_url`.

- Los 118 registros tienen titulo, provincia, URL de imagen y URL de PDF.
- **Sin municipio, sin coordenadas, sin proteccion, sin texto de descripcion, sin tipologia.**
- La documentacion completa de cada paisaje esta en el PDF enlazado (no almacenado en BD).

---

## 8. Distribucion geografica

### 8.1 Por provincia

| Provincia | Inmueble | Mueble | Inmaterial | Paisaje | Total | % |
|-----------|--------:|-------:|-----------:|--------:|------:|--:|
| Sevilla | 6.213 | 28.759 | 323 | 17 | 35.312 | 25,3% |
| Cordoba | 4.124 | 17.684 | 225 | 16 | 22.049 | 15,8% |
| Cadiz | 3.780 | 15.274 | 181 | 13 | 19.248 | 13,8% |
| Granada | 3.572 | 15.182 | 308 | 16 | 19.078 | 13,7% |
| Malaga | 2.724 | 13.256 | 231 | 11 | 16.222 | 11,6% |
| Jaen | 3.989 | 6.869 | 217 | 18 | 11.093 | 8,0% |
| Huelva | 2.691 | 5.415 | 245 | 15 | 8.366 | 6,0% |
| Almeria | 2.453 | 5.288 | 185 | 12 | 7.938 | 5,7% |

> Sevilla alberga el 25% de todos los bienes. Las 4 provincias principales acumulan el 69%. Jaen tiene la proporcion inmueble-mueble mas equilibrada, mientras que Sevilla esta muy sesgada hacia mueble.

**Problema de calidad de datos:** 27 registros tienen valores de provincia separados por comas (ej., "Huelva, Sevilla"). 1 registro de mueble tiene provincia NULL.

### 8.2 Top 10 municipios

| Municipio | Provincia | Bienes |
|-----------|----------|-------:|
| Sevilla | Sevilla | 22.278 |
| Cordoba | Cordoba | 12.754 |
| Granada | Granada | 9.599 |
| Malaga | Malaga | 6.067 |
| Cadiz | Cadiz | 5.703 |
| Almeria | Almeria | 3.838 |
| Antequera | Malaga | 3.516 |
| Jaen | Jaen | 3.479 |
| Linares | Jaen | 2.952 |
| Puerto Real | Cadiz | 2.292 |

> Las capitales de provincia dominan. Destacan Antequera (3,5K), Linares (3K) y Puerto Real (2,3K) como nucleos patrimoniales no capitalinos significativos.

---

## 9. Resumen de calidad de datos

### Fortalezas

1. **Corpus grande y bien estructurado**: 139K bienes con esquemas JSONB consistentes por tipo.
2. **Inmaterial completamente relleno**: todos los registros tienen todos los campos narrativos -- ideal para RAG.
3. **Inmueble con 100% de cobertura en campos principales**: denominacion, provincia, municipio, descripcion, datos historicos.
4. **Clasificacion rica para mueble**: tipologia (86%), materiales (86%), tecnicas (86%), estilos (72%).
5. **Buena cobertura de imagenes en general**: 62% de todos los bienes, 94% para inmaterial.

### Debilidades

| Problema | Impacto | Registros afectados |
|----------|---------|---------------------|
| **Sin coordenadas para mueble/inmaterial/paisaje** | Generacion de rutas limitada a ~5K inmueble | 134.537 (96,6%) |
| **Campo de estilo de inmueble ~94% vacio** | Consultas por estilo devuelven pocos resultados de inmueble | ~27.400 |
| **Descripcion ausente en mueble** | 14.890 registros sin texto de descripcion | 14.890 (13,8%) |
| **Registros de mueble con 2 claves JSONB** | Registros esencialmente vacios | Desconocido (min=2) |
| **Paisaje sin contenido estructurado** | Solo enlaces a PDF, no consultable | 118 |
| **Valores multiprovincia** | Rompe filtros exactos de provincia | 27 |
| **Valores de tipologia duplicados** | Ruido en arrays de tipologia (ej., mismo valor x2) | ~687 inmueble |
| **Valores en blanco en arrays** | Arrays de tipologia/periodo/estilo contienen blancos `[" "]` | Generalizado |

### Recomendaciones

1. **Geocodificacion alternativa**: usar nombres de municipio para geocodificar el 96,6% de bienes sin coordenadas (via Nominatim o similar).
2. **Limpiar valores en blanco de arrays**: eliminar entradas `" "` de arrays de tipologia, periodo y estilo durante la ingesta o en tiempo de consulta.
3. **Deduplicar arrays de tipologia**: eliminar valores repetidos dentro del mismo registro.
4. **Normalizar registros multiprovincia**: dividir en arrays o mapear a provincia principal.
5. **Marcar registros de mueble vacios**: identificar y etiquetar los registros con minimas claves JSONB (<10) para excluirlos o despriorizarlos.
6. **Extraer contenido de PDFs de paisaje**: parsear los PDFs enlazados para enriquecer los 118 registros de paisaje con texto buscable.
