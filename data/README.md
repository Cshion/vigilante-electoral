# Datos de Vigilante Electoral - Primera Vuelta 2026

Este directorio contiene datos históricos de la Primera Vuelta de las Elecciones Generales de Perú 2026, específicamente el seguimiento de la **disputa por el 2do y 3er puesto** entre **Juntos por el Perú** y **Renovación Popular**.

## 📊 Archivo de Datos

### `elecciones_2026_primera_vuelta.csv`

**Descripción:** Snapshots históricos de los resultados electorales para el 2do y 3er puesto, capturados cada 15 minutos durante el conteo oficial de la ONPE.

| Atributo | Valor |
|----------|-------|
| Formato | CSV (comma-separated values) |
| Encoding | UTF-8 |
| Filas | 2,427 (incluyendo header) |
| Columnas | 30 |
| Fecha inicio | 2026-04-18 |
| Fecha fin | 2026-05-16 (100% actas procesadas) |
| Regiones | 29 (24 departamentos + TOTAL + PERU + EXTRANJERO + especiales) |

---

## 📋 Diccionario de Campos

### Identificación y Tiempo

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | INTEGER | Identificador único del snapshot en base de datos |
| `timestamp` | TIMESTAMP (ISO 8601) | Momento exacto de la captura. Formato: `YYYY-MM-DDTHH:MM:SS.ssssss+00:00` (UTC) |
| `created_at` | TIMESTAMP (ISO 8601) | Momento de inserción en base de datos |
| `region_code` | VARCHAR(20) | Código de la región (ver tabla de códigos abajo) |

### Datos del 2do Puesto (Juntos por el Perú)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `pos2_candidate_id` | VARCHAR(20) | DNI del candidato |
| `pos2_candidate_name` | VARCHAR(255) | Nombre completo del candidato |
| `pos2_party_id` | VARCHAR(20) | Código del partido (10 = JUNTOS POR EL PERÚ) |
| `pos2_party_name` | VARCHAR(255) | Nombre del partido político |
| `pos2_votes` | BIGINT | Votos acumulados |
| `pos2_percentage` | DECIMAL(6,3) | Porcentaje sobre votos válidos |
| `pos2_percentage_emitted` | DECIMAL(6,3) | Porcentaje sobre votos emitidos |

### Datos del 3er Puesto (Renovación Popular)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `pos3_candidate_id` | VARCHAR(20) | DNI del candidato |
| `pos3_candidate_name` | VARCHAR(255) | Nombre completo del candidato |
| `pos3_party_id` | VARCHAR(20) | Código del partido (35 = RENOVACIÓN POPULAR) |
| `pos3_party_name` | VARCHAR(255) | Nombre del partido político |
| `pos3_votes` | BIGINT | Votos acumulados |
| `pos3_percentage` | DECIMAL(6,3) | Porcentaje sobre votos válidos |
| `pos3_percentage_emitted` | DECIMAL(6,3) | Porcentaje sobre votos emitidos |

### Diferencias (Campos Calculados)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `vote_gap` | BIGINT | Diferencia de votos: `pos2_votes - pos3_votes`. Positivo = JP lidera |
| `percentage_gap` | DECIMAL(6,3) | Diferencia de porcentaje: `pos2_percentage - pos3_percentage` |

### Contexto: 1er Puesto (Fuerza Popular)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `pos1_candidate_name` | VARCHAR(255) | Nombre de la candidata en 1er lugar (Keiko Fujimori) |
| `pos1_votes` | BIGINT | Votos del 1er puesto |
| `pos1_percentage` | DECIMAL(6,3) | Porcentaje del 1er puesto |

### Totales y Conteo

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `total_valid_votes` | BIGINT | Total de votos válidos (sin blancos ni nulos) |
| `total_emitted_votes` | BIGINT | Total de votos emitidos (válidos + blancos + nulos) |
| `blank_votes` | BIGINT | Votos en blanco |
| `null_votes` | BIGINT | Votos nulos |

### Progreso de Actas

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `actas_counted` | INTEGER | Número de actas procesadas |
| `actas_total` | INTEGER | Total de actas a procesar |
| `actas_percentage` | DECIMAL(6,3) | Porcentaje de actas procesadas: `(actas_counted / actas_total) * 100` |

---

## 🗺️ Códigos de Región

| Código | Región |
|--------|--------|
| `TOTAL` | Total nacional (Perú + Extranjero) |
| `PERU` | Perú (solo territorio nacional) |
| `EXTRANJERO` | Voto de peruanos en el extranjero |
| `010000` | Amazonas |
| `020000` | Áncash |
| `030000` | Apurímac |
| `040000` | Arequipa |
| `050000` | Ayacucho |
| `060000` | Cajamarca |
| `070000` | Callao |
| `080000` | Cusco |
| `090000` | Huancavelica |
| `100000` | Huánuco |
| `110000` | Ica |
| `120000` | Junín |
| `130000` | La Libertad |
| `140000` | Lambayeque |
| `150000` | Lima |
| `160000` | Loreto |
| `170000` | Madre de Dios |
| `180000` | Moquegua |
| `190000` | Pasco |
| `200000` | Piura |
| `210000` | Puno |
| `220000` | San Martín |
| `230000` | Tacna |
| `240000` | Tumbes |
| `250000` | Ucayali |

---

## 📡 Fuente de Datos

| Atributo | Valor |
|----------|-------|
| **Fuente Original** | ONPE (Oficina Nacional de Procesos Electorales) |
| **URL** | https://resultados.onpe.gob.pe |
| **API** | API de Resultados ONPE 2026 |
| **Método de Captura** | Scraping automatizado cada 15 minutos |
| **Almacenamiento** | Supabase PostgreSQL |
| **Período de Captura** | 18 de abril - 16 de mayo 2026 |

---

## 📈 Resultados Finales (100% actas)

| Posición | Candidato | Partido | Votos | % |
|----------|-----------|---------|-------|---|
| 1º | Keiko Sofía Fujimori Higuchi | Fuerza Popular | ~2.7M | ~17% |
| **2º** | **Roberto Helbert Sánchez Palomino** | **Juntos por el Perú** | **2,015,114** | **12.031%** |
| **3º** | **Rafael Bernardo López Aliaga Cazorla** | **Renovación Popular** | **1,993,905** | **11.904%** |

**Diferencia final:** 21,209 votos (0.127%)

---


## 📜 Licencia

Datos electorales de dominio público. La ONPE publica los resultados oficiales como información de acceso público.

---

## 🤝 Proyecto

Este dataset forma parte del proyecto **Vigilante Electoral**, una herramienta de monitoreo en tiempo real de la disputa por el segundo lugar en la Primera Vuelta Electoral Perú 2026.

- **Repositorio:** [vigilante_electoral](https://github.com/...)
- **Frontend:** Next.js + React
- **Backend:** FastAPI + Python
- **Base de datos:** Supabase (PostgreSQL)
