# Reggie — History

## Project Context

**Project:** Vigilante Electoral - Electoral monitoring application for Peru 2026 elections
**Tech Stack:** Next.js (frontend), FastAPI (backend), Supabase (database), Vercel (deployment)
**User:** Aaron

This is a real-time election results visualization app that scrapes data from ONPE (Peru's electoral authority) and displays vote counts, trends, and notifications.

## Security-Relevant Context

- **Backend:** FastAPI with CORS configuration, Supabase client for database access
- **Frontend:** Next.js with environment variables for API URLs
- **Database:** Supabase PostgreSQL with RLS considerations
- **External Data:** Scrapes from ONPE website (third-party data)
- **Deployment:** Planning Vercel deployment

## Learnings

### Pre-Deployment Security Review (2026-04-18)

**Audit Scope:** Backend (FastAPI), Frontend (Next.js), Dependencies, Configuration

#### Key Findings

1. **CORS Configuration** ([config.py](backend/app/config.py#L14-L20))
   - Production origin properly whitelisted: `vigilante-electoral.vercel.app`
   - Local dev origins included (localhost, 192.168.x.x) - must review for prod
   
2. **Environment Variables**
   - `.env` files properly gitignored in both backend and frontend
   - Secrets not hardcoded in code (verified via grep)
   - Using pydantic-settings for secure env loading

3. **Scrape Endpoint Auth** ([scrape.py](backend/app/routers/scrape.py#L54-L79))
   - CRON_SECRET auth implemented via Bearer token
   - Falls back to open access if no secrets configured (dev mode risk)

4. **Database Security**
   - RLS enabled on all tables in Supabase
   - Using Supabase client (parameterized queries, no raw SQL injection risk)
   
5. **Health Endpoint Info Leak** ([main.py](backend/app/main.py#L36-L51))
   - Exposes partial SUPABASE_URL (first 30 chars) - minor info leak

6. **Debug Mode** ([config.py](backend/app/config.py#L12))
   - DEBUG defaults to False - correct for production

7. **Frontend XSS**
   - No dangerouslySetInnerHTML usage found
   - React auto-escapes rendered content
   - Data from ONPE is numeric/controlled strings only

8. **Dependencies**
   - FastAPI 0.109.0 (current as of audit date)
   - Next.js 16.2.4 (current)
   - No known critical CVEs in requirements.txt

#### Patterns to Enforce

- Always verify CRON_SECRET is set in production environment
- Remove local dev origins from ALLOWED_ORIGINS before prod deploy
- Consider rate limiting on public endpoints to prevent abuse
