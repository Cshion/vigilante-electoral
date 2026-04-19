# Matt — History

## Project Context

**Project:** vigilante_electoral — Electoral monitoring application
**User:** Aaron
**Stack:** FastAPI backend, Next.js 16 frontend, Supabase (database), Vercel (deployment)
**Purpose:** Monitor and track electoral results from Peru's ONPE website, showing vote changes over time

## Key Data Source

- **URL:** https://resultadoelectoral.onpe.gob.pe/main/presidenciales
- **Update frequency:** Every 15 minutes
- **Data:** Vote counts by candidate

## Key Files

- `backend/app/services/scraper.py` — ONPE data fetching, parsing, and caching
- `backend/app/routers/results.py` — Electoral results API endpoints
- `backend/app/services/analyzer.py` — Vote change analysis

## Learnings

### 2026-04-17: Rivalry Tracking Implementation
- The scraper uses a TTLCache (30s) keyed by `{region_code}:{top_n}:{rivalry_only}` - cache keys MUST include all parameters that affect output
- ONPE API party codes: JUNTOS POR EL PERÚ = "10", RENOVACIÓN POPULAR = "35"
- Router responses explicitly construct return objects - new fields from scraper won't appear unless added to router response dict
- rivalry_only mode is the DEFAULT for regional queries (scrape_by_region) but NOT for national (scrape_presidential_results)

## Patterns

- When adding new response fields in scraper, ALWAYS check the router layer to ensure the field is passed through
- Cache key design matters — include all parameters that change the response

### 2026-04-19: Projection Algorithm Design
- Tabla `position_snapshots` tiene columnas clave para proyección: `actas_percentage`, `actas_counted`, `actas_total`
- Algoritmo lineal simple (`votes × 100 / actas_pct`) es muy impreciso al inicio del conteo
- Mejor enfoque: Trend-Based Projection con Exponential Weighted Average (EWA)
- Fórmula: `growth_rate = Δvotes / Δactas`, luego `projected = current + (rate × remaining_actas)`
- Para confiabilidad: usar últimos N snapshots con peso decreciente (decay=0.7)
- Edge case importante: trackear por `candidate_id` no por posición, porque pueden swapear
