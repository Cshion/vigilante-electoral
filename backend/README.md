# Vigilante Electoral - Backend

FastAPI backend for monitoring Peruvian electoral results from ONPE.

## Quick Start

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your Supabase credentials

# Run the server
uvicorn app.main:app --reload --port 8000
```

## Environment Variables

Create a `.env` file:

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
CRON_SECRET=your-secret-for-scrape-endpoint
DEBUG=True
```

## API Endpoints

### Results
- `GET /results/current` - Latest presidential results with deltas
- `GET /results/history?hours=24` - Historical snapshots
- `GET /results/candidates/{id}` - Single candidate history
- `GET /results/deltas` - Vote changes between latest snapshots

### Snapshots
- `GET /snapshots/` - List all snapshots
- `GET /snapshots/{id}` - Single snapshot details

### System
- `GET /health` - Health check
- `POST /api/scrape` - Trigger data scrape (protected)

## Database Setup

Run this SQL in Supabase:

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
```

## Data Scraping

The scraper fetches data from ONPE's website every 15 minutes.
Set up a cron job to call `/api/scrape` with the CRON_SECRET.

Example with cron-job.org:
```
URL: https://your-api.vercel.app/api/scrape
Method: POST
Header: Authorization: Bearer your-secret
Schedule: */15 * * * *
```
