# Alejandro — History

## Project Context

**Project:** vigilante_electoral — Electoral monitoring application
**User:** Aaron
**Stack:** FastAPI backend, Next.js 16 frontend, Supabase (database), Vercel (deployment)
**Purpose:** Monitor and track electoral results from Peru's ONPE website, showing vote changes over time

## Key Files

- (to be populated as project develops)

## Learnings

### 2026-04-17: Arquitectura Scraping Separado
- Los endpoints actuales (`/results/live/{region}`, `/positions/current`) consultan ONPE directamente en cada request — causa latencia alta e inconsistencia
- Nueva arquitectura: separar lectura (DB) de escritura (scrape)
- El scraper ya tiene `REGIONS` dict con las 27 regiones (NACIONAL + EXTRANJERO + 25 departamentos)
- `position_snapshots` ya tiene columna `region_code` — no se necesita migración
- Rate limit ONPE: Semaphore(3) es seguro, más paralelos podría causar ban
- Vercel Hobby tiene timeout de 10s (insuficiente para scrape de 27 regiones); necesita Pro o alternativa

## Patterns

### Event-Driven Scraping
```
Event Bus/Cron 
    → POST /api/scrape (con API key)
    → Scraper consulta ONPE (parallel, rate limited)
    → Solo guarda si votos cambiaron
    → Endpoints públicos solo leen DB
```

### Archivos Clave Backend
- `backend/app/routers/results.py` — resultados electorales por región
- `backend/app/routers/positions.py` — tracking 2do/3er puesto
- `backend/app/services/scraper.py` — cliente ONPE con cache y semaphore
