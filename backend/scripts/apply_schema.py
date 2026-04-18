"""Script para aplicar el esquema a Supabase."""
import os
from supabase import create_client

# Cargar variables de entorno del archivo .env
from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: SUPABASE_URL y SUPABASE_KEY deben estar configuradas en .env")
    exit(1)

print(f"✅ URL: {SUPABASE_URL}")
print(f"✅ KEY: {SUPABASE_KEY[:20]}...")

# Crear cliente
client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Schema SQL a aplicar
SCHEMA_SQL = """
-- Verificar y crear tablas si no existen

-- TABLA: position_snapshots
CREATE TABLE IF NOT EXISTS position_snapshots (
  id BIGSERIAL PRIMARY KEY,
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  
  pos2_candidate_id VARCHAR(20) NOT NULL,
  pos2_candidate_name VARCHAR(255) NOT NULL,
  pos2_party_name VARCHAR(255) NOT NULL,
  pos2_party_id VARCHAR(20),
  pos2_votes BIGINT NOT NULL,
  pos2_percentage DECIMAL(6,3) NOT NULL,
  pos2_percentage_emitted DECIMAL(6,3),
  
  pos3_candidate_id VARCHAR(20) NOT NULL,
  pos3_candidate_name VARCHAR(255) NOT NULL,
  pos3_party_name VARCHAR(255) NOT NULL,
  pos3_party_id VARCHAR(20),
  pos3_votes BIGINT NOT NULL,
  pos3_percentage DECIMAL(6,3) NOT NULL,
  pos3_percentage_emitted DECIMAL(6,3),
  
  vote_gap BIGINT GENERATED ALWAYS AS (pos2_votes - pos3_votes) STORED,
  percentage_gap DECIMAL(6,3) GENERATED ALWAYS AS (pos2_percentage - pos3_percentage) STORED,
  
  total_valid_votes BIGINT,
  total_emitted_votes BIGINT,
  blank_votes BIGINT,
  null_votes BIGINT,
  
  pos1_candidate_name VARCHAR(255),
  pos1_votes BIGINT,
  pos1_percentage DECIMAL(6,3),
  
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- TABLA: position_changes
CREATE TABLE IF NOT EXISTS position_changes (
  id BIGSERIAL PRIMARY KEY,
  snapshot_id BIGINT REFERENCES position_snapshots(id),
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  pos2_vote_change BIGINT DEFAULT 0,
  pos2_percentage_change DECIMAL(6,3) DEFAULT 0,
  pos3_vote_change BIGINT DEFAULT 0,
  pos3_percentage_change DECIMAL(6,3) DEFAULT 0,
  gap_change BIGINT DEFAULT 0,
  position_swap BOOLEAN DEFAULT FALSE,
  minutes_since_last INT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- TABLA: candidates
CREATE TABLE IF NOT EXISTS candidates (
  id VARCHAR(20) PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  party_name VARCHAR(255),
  party_id VARCHAR(20),
  candidate_image_url TEXT,
  party_image_url TEXT,
  first_seen_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
"""

print("\n📋 Aplicando esquema...")

# Supabase Python client no puede ejecutar SQL directo,
# pero podemos verificar la conexión haciendo una consulta
try:
    # Intentar leer de la tabla (verificará si existe)
    response = client.table("position_snapshots").select("id").limit(1).execute()
    print(f"✅ Tabla position_snapshots existe. Registros: {len(response.data)}")
except Exception as e:
    print(f"⚠️ Tabla position_snapshots no existe o error: {e}")
    print("\n🔧 Debes ejecutar el SQL del archivo supabase/schema.sql en el SQL Editor de Supabase")

try:
    response = client.table("position_changes").select("id").limit(1).execute()
    print(f"✅ Tabla position_changes existe. Registros: {len(response.data)}")
except Exception as e:
    print(f"⚠️ Tabla position_changes no existe o error: {e}")

try:
    response = client.table("candidates").select("id").limit(1).execute()
    print(f"✅ Tabla candidates existe. Registros: {len(response.data)}")
except Exception as e:
    print(f"⚠️ Tabla candidates no existe o error: {e}")

print("\n" + "="*60)
print("Para aplicar el esquema completo, ejecuta el contenido de:")
print("  supabase/schema.sql")
print("En el SQL Editor de tu proyecto Supabase:")
print(f"  {SUPABASE_URL.replace('.supabase.co', '.supabase.co/project/_/sql')}")
print("="*60)
