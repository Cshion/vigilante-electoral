# Vigilante Electoral 🗳️

<p align="center">
  <strong>Monitoreo en tiempo real de resultados electorales presidenciales del Perú</strong>
</p>

<p align="center">
  <a href="https://vigilante-electoral.godatify.com/">🌐 Demo en Vivo</a> •
  <a href="#características">Características</a> •
  <a href="#arquitectura">Arquitectura</a> •
  <a href="#instalación">Instalación</a> •
  <a href="#api">API</a>
</p>

---

## 🎯 ¿Qué es?

Vigilante Electoral es una aplicación que monitorea los resultados de las elecciones presidenciales del Perú en tiempo real, obteniendo datos directamente de la **ONPE** (Oficina Nacional de Procesos Electorales). 

El enfoque principal es el seguimiento de la **disputa por el 2do y 3er puesto**, almacenando snapshots cada 15 minutos para analizar la evolución de la contienda.

**👉 [Ver Demo](https://vigilante-electoral.godatify.com/)**

## ✨ Características

| Feature | Descripción |
|---------|-------------|
| 📊 **Dashboard interactivo** | Resultados en vivo con actualización automática |
| 📈 **Evolución histórica** | Visualización de cambios de votos en el tiempo |
| 🔔 **Notificaciones** | Alertas cuando hay cambios significativos |
| 🗺️ **Filtro por región** | Ver resultados nacionales, por departamento o extranjero |
| 📱 **Mobile-first** | Diseño responsivo optimizado para móviles |
| ⚡ **Cache inteligente** | 5 min TTL con invalidación automática |
| 🔒 **Seguridad** | CORS configurable, endpoints protegidos |

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                         ONPE Website                             │
│  https://resultadoelectoral.onpe.gob.pe/main/presidenciales     │
└─────────────────────────────────┬───────────────────────────────┘
                                  │ Scraping (cada 15 min)
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (EC2)                         │
│  • fastapi-cache2 (InMemory, 5 min TTL)                         │
│  • Middleware ignora Cache-Control del cliente                   │
│  POST /api/scrape → invalida cache → GET /results/live/*        │
└─────────────────────────────────┬───────────────────────────────┘
                                  │ Supabase Client
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Supabase (PostgreSQL)                       │
│  position_snapshots │ change_notifications                       │
└─────────────────────────────────┬───────────────────────────────┘
                                  │ REST API
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Next.js Frontend (Vercel)                     │
│  • SWR con dedupe 5 min                                         │
│  • Assets estáticos: cache 1 año                                │
│  Dashboard │ Evolución │ Notificaciones │ Selector Región       │
└─────────────────────────────────────────────────────────────────┘
```

## 🛠️ Stack Tecnológico

| Capa | Tecnología |
|------|------------|
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind CSS 4, SWR, Recharts |
| **Backend** | FastAPI, Python 3.12, fastapi-cache2, BeautifulSoup4 |
| **Database** | Supabase (PostgreSQL) |
| **Deployment** | Vercel (frontend), EC2 Ubuntu 24.04 (backend) |

## 📁 Estructura del Proyecto

```
vigilante_electoral/
├── backend/
│   ├── app/
│   │   ├── main.py              # App + CORS + Cache middleware
│   │   ├── config.py            # Variables de entorno
│   │   ├── database.py          # Cliente Supabase
│   │   ├── routers/
│   │   │   ├── results.py       # GET /results/*
│   │   │   ├── positions.py     # GET /positions/*
│   │   │   ├── scrape.py        # POST /api/scrape
│   │   │   └── notifications.py # GET /api/notifications
│   │   └── services/
│   │       └── scraper.py       # Obtiene datos de ONPE
│   ├── scripts/
│   │   ├── setup-ec2.sh         # Setup servidor
│   │   └── deploy-to-ec2.sh     # Deploy automático
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx         # Dashboard principal
│   │   │   └── globals.css
│   │   ├── components/
│   │   │   ├── RegionSelector.tsx
│   │   │   ├── RivalryDisplay.tsx
│   │   │   ├── VoteEvolution.tsx
│   │   │   ├── NotificationPanel.tsx
│   │   │   └── LiveIndicator.tsx
│   │   ├── hooks/
│   │   │   └── useResults.ts    # SWR hooks
│   │   └── lib/
│   │       ├── api.ts           # Fetcher
│   │       ├── types.ts         # TypeScript types
│   │       └── utils.ts         # Helpers
│   ├── vercel.json              # Headers para cache de assets
│   └── package.json
├── supabase/
│   ├── schema.sql               # DDL completo
│   └── migrations/
└── docs/
    └── ARCHITECTURE.md
```

---

## 🚀 Instalación

### Prerequisitos

- Node.js 18+ y npm
- Python 3.12+
- Cuenta en [Supabase](https://supabase.com)

### 1. Clonar el repositorio

```bash
git clone https://github.com/Cshion/vigilante-electoral.git
cd vigilante-electoral
```

### 2. Configurar Supabase

1. Crea un proyecto en [Supabase](https://supabase.com)
2. Ejecuta `supabase/schema.sql` en el SQL Editor
3. Copia tu **URL** y **service_role key** desde Project Settings > API

### 3. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configurar variables
cat > .env << EOF
DEBUG=true
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_KEY=tu-service-role-key
CRON_SECRET=un-secret-seguro
ALLOWED_ORIGINS=http://localhost:3000
EOF

# Iniciar servidor
uvicorn app.main:app --reload --port 8000
```

### 4. Frontend

```bash
cd frontend
npm install

cat > .env.local << EOF
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF

npm run dev
```

Visita `http://localhost:3000` 🎉

---

## 📡 API Endpoints

### Resultados en vivo

| Método | Endpoint | Cache | Descripción |
|--------|----------|-------|-------------|
| GET | `/results/live/regions` | 1 hora | Lista de regiones |
| GET | `/results/live/{region}` | 5 min | Resultados por región |
| GET | `/results/live/actas/{region}` | 5 min | Progreso de actas |

### Historial

| Método | Endpoint | Cache | Descripción |
|--------|----------|-------|-------------|
| GET | `/positions/history` | 5 min | Historial de posiciones |

### Notificaciones

| Método | Endpoint | Cache | Descripción |
|--------|----------|-------|-------------|
| GET | `/api/notifications` | 5 min | Cambios recientes |

### Scraping (protegido)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/scrape` | Ejecutar scraping (requiere `X-Cron-Secret`) |
| POST | `/api/scrape/all-regions` | Scrape todas las regiones |

---

## ⚙️ Variables de Entorno

### Backend (`.env`)

| Variable | Descripción | Requerido |
|----------|-------------|-----------|
| `SUPABASE_URL` | URL del proyecto Supabase | ✅ |
| `SUPABASE_KEY` | Service role key de Supabase | ✅ |
| `CRON_SECRET` | Secret para proteger `/api/scrape` | ✅ |
| `ALLOWED_ORIGINS` | Origins permitidos (comma-separated) | ✅ |
| `CORS_ORIGIN_REGEX` | Regex para origins dinámicos (ej: Vercel previews) | ❌ |
| `DEBUG` | Habilita docs y logs detallados | ❌ |

### Frontend (`.env.local`)

| Variable | Descripción | Requerido |
|----------|-------------|-----------|
| `NEXT_PUBLIC_API_URL` | URL del backend | ✅ |

---

## 🌐 Deployment

### Frontend → Vercel

1. Importa el repositorio en [Vercel](https://vercel.com)
2. Root Directory: `frontend`
3. Variables de entorno:
   ```
   NEXT_PUBLIC_API_URL=https://tu-api.com
   ```

### Backend → EC2

```bash
# Setup inicial (una vez)
scp -i key.pem backend/scripts/setup-ec2.sh ubuntu@IP:~/
ssh -i key.pem ubuntu@IP "chmod +x setup-ec2.sh && sudo ./setup-ec2.sh"

# Deploy código
cd backend/scripts
./deploy-to-ec2.sh <IP> <path-to-pem>

# Configurar .env en servidor
ssh -i key.pem ubuntu@IP "sudo nano /opt/vigilante-electoral/.env"
```

---

## 📊 Estrategia de Cache

| Capa | TTL | Estrategia |
|------|-----|------------|
| **Backend (fastapi-cache2)** | 5 min | InMemory, invalidación en scrape |
| **Frontend (SWR)** | 5 min | Dedupe, sin revalidateOnFocus |
| **Assets estáticos** | 1 año | Vercel headers, immutable |

---

## 🔧 Comandos Útiles

```bash
# Desarrollo local
cd backend && source venv/bin/activate && uvicorn app.main:app --reload
cd frontend && npm run dev

# Servidor EC2
sudo systemctl status vigilante-electoral
sudo journalctl -u vigilante-electoral -f
sudo systemctl restart vigilante-electoral
```

---

## 📄 Licencia

MIT License

---

<p align="center">
  <strong>👉 <a href="https://vigilante-electoral.godatify.com/">Ver Demo en Vivo</a></strong>
</p>
