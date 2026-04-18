# Squad Decisions

## Active Decisions

### Arquitectura para Resultados por Departamento (2026-04-17)
**By:** Alejandro (Lead)
**Requested by:** Aaron

#### Resumen
Diseño del feature para visualizar resultados electorales por departamento/región además de los nacionales.

#### Decisiones Tomadas
| Decisión | Opción elegida | Razón |
|----------|----------------|-------|
| Scraping | On-demand + cache 30s | Evitar bloqueo ONPE |
| Base de datos | Columna `region_code` | Simplicidad, backward compat |
| Rate limit | Semaphore(2) concurrent | Proteger contra ban |
| API design | `/live/{region_code}` | RESTful, más claro |

#### Endpoints
- `GET /results/live/{region_code}` - Resultados de una región específica
- `GET /results/live/regions` - Lista de regiones disponibles

#### Capas de Caché
- Frontend (SWR): 5s stale, 15s refresh
- Backend (TTLCache): 30s TTL por región
- Rate Limit: 2 concurrent requests a ONPE

---

### Frontend Responsive + Colores Candidatos (2026-04-17)
**By:** Kate (Frontend Dev)

#### Cambios Implementados
1. **Responsive Desktop:** max-w-4xl, tamaños de fuente escalados con md: breakpoints
2. **Colores por Candidato:**
   - Sánchez Palomino: Rojo/Verde (gradiente)
   - López Aliaga: Celeste (sky)
3. **Stats actualizados:** Removidos votos válidos/emitidos, ahora muestra % Blancos y % Nulos
4. **Evolución con hora:** Muestra hora exacta (HH:MM:SS) y fecha de cada cambio ONPE

### Backend: Endpoint ONPE + DB Obligatoria (2026-04-17) 
**By:** Matt (Backend Dev)

#### Cambios
1. **Endpoint ONPE corregido:** `?idEleccion=10&tipoFiltro=eleccion` (votos totales nacionales)
2. **DB obligatoria:** Health check falla si Supabase no conecta (503)
3. **Historial con %:** Endpoint `/positions/history` ahora incluye `blancos_porcentaje` y `nulos_porcentaje`

---

### Smart Storage Strategy: Only Save Changes (2026-04-17)
**By:** Alejandro (Lead)
**Requested by:** Aaron

#### Problem Solved
Previously storing a snapshot every 15 minutes regardless of vote changes. Now we only store when votes actually change.

#### Implementation
1. **Backend:** `has_votes_changed()` method compares pos2/pos3 votes before inserting
2. **Database:** Only meaningful snapshots stored, reducing ~80-90% bloat
3. **Frontend:** Shows "Solo se registra cuando los votos cambian" to explain gaps

#### Mobile-First Light Theme (2026-04-17)
**By:** Kate (Frontend Dev)

- Light background (#fafafa) for outdoor readability
- Mobile-first design with rivalry as primary focus
- Vote gap prominently displayed with color coding (red = shrinking, green = growing)
- Evolution chart showing only actual changes

---

### Architecture Decision: vigilante_electoral (2026-04-18)
**By:** Alejandro (Lead)

#### Stack Selection
- **Backend:** FastAPI (async, fast, Python ecosystem for scraping)
- **Frontend:** Next.js 16 App Router (SSR, Vercel native)
- **Database:** Supabase (PostgreSQL, real-time subscriptions available)
- **Deployment:** Vercel (unified platform)

#### Data Strategy
1. Store complete snapshots every 15 min (not deltas) — enables flexible queries
2. Calculate deltas on-the-fly from consecutive snapshots
3. JSONB for candidate data — flexible schema for varying elections

#### Update Mechanism
- External cron triggers `/api/scrape` every 15 minutes
- Frontend polls every 15 seconds for fresh data
- WebSocket upgrade available if real-time demand grows

#### Key Trade-offs
- **Snapshot vs Delta storage:** Chose snapshots for auditability + simpler queries
- **Polling vs WebSocket:** Chose polling for simplicity, WebSocket ready
- **Monorepo vs Separate:** Monorepo with `/backend` and `/frontend` folders

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here
- Keep history focused on work, decisions focused on direction
