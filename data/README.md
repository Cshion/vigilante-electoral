# Datos de Vigilante Electoral - Primera Vuelta 2026

Datos históricos de la Primera Vuelta de las Elecciones Generales de Perú 2026, con seguimiento de los **3 principales partidos**: Fuerza Popular, Juntos por el Perú y Renovación Popular.

## 📊 Archivo de Datos

### `elecciones_2026_total_resultados.csv`

Snapshots históricos de los resultados electorales **a nivel nacional (TOTAL)**, capturados durante el conteo oficial de la ONPE.

| Atributo | Valor |
|----------|-------|
| Formato | CSV (UTF-8) |
| Registros | 515 |
| Columnas | 14 |
| Fecha inicio | 2026-04-18 |
| Fecha fin | 2026-05-16 (100% actas) |
| Cobertura | Total nacional |

### Resultado Final (100% actas)

| Partido | Votos | Porcentaje |
|---------|------:|----------:|
| **Fuerza Popular** | 2,877,678 | 17.18% |
| **Juntos por el Perú** | 2,015,114 | 12.03% |
| **Renovación Popular** | 1,993,905 | 11.90% |

---

## 📋 Diccionario de Campos

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `timestamp` | TIMESTAMP (ISO 8601) | Momento de captura (UTC) |
| `actas_counted` | INTEGER | Actas procesadas |
| `actas_total` | INTEGER | Total de actas |
| `actas_pct` | DECIMAL | Porcentaje de actas procesadas |
| `fuerza_popular_votes` | BIGINT | Votos de Fuerza Popular (Keiko Fujimori) |
| `fuerza_popular_pct` | DECIMAL | Porcentaje sobre votos válidos |
| `juntos_peru_votes` | BIGINT | Votos de Juntos por el Perú (Sánchez) |
| `juntos_peru_pct` | DECIMAL | Porcentaje sobre votos válidos |
| `renovacion_popular_votes` | BIGINT | Votos de Renovación Popular (López Aliaga) |
| `renovacion_popular_pct` | DECIMAL | Porcentaje sobre votos válidos |
| `total_valid_votes` | BIGINT | Total de votos válidos |
| `total_emitted_votes` | BIGINT | Total de votos emitidos |
| `blank_votes` | BIGINT | Votos en blanco |
| `null_votes` | BIGINT | Votos nulos |

---

## 🏛️ Partidos Políticos

| Partido | Candidato | ID ONPE |
|---------|-----------|---------|
| Fuerza Popular | Keiko Fujimori | - |
| Juntos por el Perú | Roberto Sánchez | 10 |
| Renovación Popular | Rafael López Aliaga | 35 |

---

## 📡 Fuente de Datos

| Atributo | Valor |
|----------|-------|
| **Fuente** | ONPE (Oficina Nacional de Procesos Electorales) |
| **URL** | https://resultados.onpe.gob.pe |
| **Período** | 18 abril - 16 mayo 2026 |

---

## 📜 Licencia

Datos electorales de dominio público publicados por ONPE.
