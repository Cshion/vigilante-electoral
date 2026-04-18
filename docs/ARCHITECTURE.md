# vigilante_electoral - System Architecture

## Overview

Electoral monitoring application for Peru's presidential elections. Fetches data from ONPE (Oficina Nacional de Procesos Electorales), stores historical snapshots, and provides interactive visualizations of vote changes over time.

## Stack

| Layer | Technology | Deployment |
|-------|------------|------------|
| Frontend | Next.js 16 (App Router) | Vercel |
| Backend | FastAPI | Vercel Serverless |
| Database | Supabase (PostgreSQL) | Supabase Cloud |
| Charts | Recharts | — |

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         ONPE Website                             │
│  https://resultadoelectoral.onpe.gob.pe/main/presidenciales     │
└─────────────────────────────────┬───────────────────────────────┘
                                  │ HTTP (every 15 min)
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                             │
│  /api/scrape (cron) → /api/results/current → /api/results/history│
└─────────────────────────────────┬───────────────────────────────┘
                                  │ Supabase Client
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Supabase (PostgreSQL)                       │
│  election_snapshots | candidates | results_history               │
└─────────────────────────────────┬───────────────────────────────┘
                                  │ REST API
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Next.js Frontend                            │
│  Dashboard | Charts | Real-time updates (polling 15s)            │
└─────────────────────────────────────────────────────────────────┘
```

## Database Schema

### Table: `election_snapshots`

Stores complete snapshots of election results every 15 minutes.

```sql
CREATE TABLE election_snapshots (
  id BIGSERIAL PRIMARY KEY,
  election_type VARCHAR(50) NOT NULL DEFAULT 'PRESI',
  data JSONB NOT NULL,
  actas_percentage FLOAT,
  total_valid_votes BIGINT,
  total_emitted_votes BIGINT,
  timestamp TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_snapshots_type_time ON election_snapshots(election_type, timestamp DESC);
CREATE INDEX idx_snapshots_timestamp ON election_snapshots(timestamp DESC);
```

### Table: `candidates`

Normalized candidate information.

```sql
CREATE TABLE candidates (
  id VARCHAR(20) PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  party_name VARCHAR(255),
  party_id VARCHAR(20),
  candidate_image_url TEXT,
  party_image_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### JSONB Structure in `data` column

```json
{
  "candidates": [
    {
      "id": "16002918",
      "name": "KEIKO SOFIA FUJIMORI HIGUCHI",
      "party_name": "FUERZA POPULAR",
      "party_id": "00000010",
      "votes": 2686993,
      "percentage": 17.05,
      "candidate_image_url": "https://...",
      "party_image_url": "https://..."
    }
  ],
  "totals": {
    "valid_votes": 15753821,
    "blank_votes": 2199007,
    "null_votes": 945021,
    "emitted_votes": 18897849
  }
}
```

## API Endpoints

### Backend (FastAPI)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/results/current` | GET | Latest election results |
| `/results/history` | GET | Historical snapshots (paginated) |
| `/results/candidates/{id}` | GET | Single candidate vote history |
| `/snapshots/` | GET | List all snapshots |
| `/api/scrape` | POST | Trigger data scrape (cron protected) |

### Query Parameters

- `election_type`: `PRESI` (default), `CONGRESO`, etc.
- `limit`: Number of results (1-100, default 20)
- `from_date`: Filter snapshots after date
- `to_date`: Filter snapshots before date

## Frontend Pages

| Route | Description |
|-------|-------------|
| `/` | Dashboard with current results + live updates |
| `/history` | 24-hour historical view with charts |
| `/candidate/[id]` | Individual candidate details |

## Real-time Updates

Frontend polls backend every 15 seconds for new data:

```typescript
// useResults hook
const { data, error, isLoading } = useSWR(
  '/api/results/current',
  fetcher,
  { refreshInterval: 15000 }
);
```

## Delta Calculation

Vote changes calculated on-the-fly comparing consecutive snapshots:

```python
delta = current_votes - previous_votes
percentage_change = current_percentage - previous_percentage
```

## Deployment

### Vercel (Frontend + Backend)

```
vercel.json
├── rewrites: /api/* → backend
├── functions: backend/app/main.py
└── build: next build
```

### Environment Variables

```
# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...  # For backend only

# API
NEXT_PUBLIC_API_URL=https://api.vigilante-electoral.vercel.app
CRON_SECRET=xxx  # For scrape endpoint auth
```

## Cron Job

External cron (cron-job.org or Vercel Cron) triggers scrape every 15 minutes:

```
POST /api/scrape
Authorization: Bearer {CRON_SECRET}
```
