#!/usr/bin/env python3
"""
Export all API data to static JSON files for frontend.
This converts the dynamic site to a static one.
"""
import os
import sys
import json
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

# Config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Cutoff date - only include data up to this date (final election results)
CUTOFF_DATE = "2026-05-16T23:59:59+00:00"

# Output to frontend/public/data
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "..", "..", "frontend", "public", "data")

# Region name mapping
REGION_NAMES = {
    "TOTAL": "Total (Perú + Extranjero)",
    "PERU": "Perú (territorio nacional)",
    "EXTRANJERO": "Voto Extranjero",
    "NACIONAL": "Nacional",
    "010000": "Amazonas",
    "020000": "Áncash",
    "030000": "Apurímac",
    "040000": "Arequipa",
    "050000": "Ayacucho",
    "060000": "Cajamarca",
    "070000": "Callao",
    "080000": "Cusco",
    "090000": "Huancavelica",
    "100000": "Huánuco",
    "110000": "Ica",
    "120000": "Junín",
    "130000": "La Libertad",
    "140000": "Lambayeque",
    "150000": "Lima",
    "160000": "Loreto",
    "170000": "Madre de Dios",
    "180000": "Moquegua",
    "190000": "Pasco",
    "200000": "Piura",
    "210000": "Puno",
    "220000": "San Martín",
    "230000": "Tacna",
    "240000": "Tumbes",
    "250000": "Ucayali",
}

REGION_CATEGORIES = {
    "TOTAL": "total",
    "PERU": "peru",
    "EXTRANJERO": "extranjero",
}


def get_latest_snapshot_by_region(client):
    """Get the latest snapshot for each region (before cutoff date)."""
    print(f"  📥 Fetching latest snapshots (until {CUTOFF_DATE[:10]})...")
    
    response = client.table("position_snapshots").select("*").lte("timestamp", CUTOFF_DATE).order("timestamp", desc=True).limit(1000).execute()
    
    if not response.data:
        return {}
    
    # Group by region and get latest
    latest_by_region = {}
    for row in response.data:
        region = row['region_code']
        if region not in latest_by_region:
            latest_by_region[region] = row
    
    print(f"     ✅ {len(latest_by_region)} regions found")
    return latest_by_region


def get_all_snapshots_by_region(client):
    """Get all snapshots grouped by region for history (until cutoff date)."""
    print(f"  📥 Fetching all snapshots for history (until {CUTOFF_DATE[:10]})...")
    
    all_data = []
    offset = 0
    page_size = 1000
    
    while True:
        response = client.table("position_snapshots").select("*").lte("timestamp", CUTOFF_DATE).order("timestamp", desc=False).range(offset, offset + page_size - 1).execute()
        if not response.data:
            break
        all_data.extend(response.data)
        print(f"     Fetched {len(all_data)} records...")
        if len(response.data) < page_size:
            break
        offset += page_size
    
    # Group by region
    by_region = defaultdict(list)
    for row in all_data:
        by_region[row['region_code']].append(row)
    
    print(f"     ✅ {len(all_data)} total snapshots across {len(by_region)} regions")
    return dict(by_region)


def get_notifications(client, limit=100, hours=168):
    """Get recent notifications."""
    print("  📥 Fetching notifications...")
    
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    
    response = client.table("change_notifications").select("*").gte("timestamp", cutoff).order("timestamp", desc=True).limit(limit).execute()
    
    notifications = response.data or []
    print(f"     ✅ {len(notifications)} notifications")
    return notifications


def format_live_results(snapshot):
    """Format a snapshot as LiveResults API response."""
    region_code = snapshot['region_code']
    region_name = REGION_NAMES.get(region_code, region_code)
    
    # Build candidates array - ONLY pos2 and pos3 (Juntos and Renovación)
    # This matches the original API which returned top_n=2 for the rivalry
    candidates = [
        {
            "id": snapshot.get('pos2_candidate_id', 'pos2'),
            "name": snapshot.get('pos2_candidate_name', 'N/A'),
            "party_name": snapshot.get('pos2_party_name', 'JUNTOS POR EL PERÚ'),
            "party_id": snapshot.get('pos2_party_id', '10'),
            "votes": snapshot.get('pos2_votes', 0),
            "percentage": snapshot.get('pos2_percentage', 0),
            "percentage_emitted": snapshot.get('pos2_percentage_emitted', 0),
        },
        {
            "id": snapshot.get('pos3_candidate_id', 'pos3'),
            "name": snapshot.get('pos3_candidate_name', 'N/A'),
            "party_name": snapshot.get('pos3_party_name', 'RENOVACIÓN POPULAR'),
            "party_id": snapshot.get('pos3_party_id', '35'),
            "votes": snapshot.get('pos3_votes', 0),
            "percentage": snapshot.get('pos3_percentage', 0),
            "percentage_emitted": snapshot.get('pos3_percentage_emitted', 0),
        }
    ]
    
    # Determine rivalry (between pos2 and pos3)
    vote_gap = snapshot.get('vote_gap', 0)
    leader = "POS2" if vote_gap >= 0 else "POS3"
    
    return {
        "election_type": "PRESI",
        "region_code": region_code,
        "region_name": region_name,
        "timestamp": snapshot.get('timestamp', ''),
        "candidates": candidates,
        "totals": {
            "valid_votes": snapshot.get('total_valid_votes', 0),
            "blank_votes": snapshot.get('blank_votes', 0),
            "null_votes": snapshot.get('null_votes', 0),
            "emitted_votes": snapshot.get('total_emitted_votes', 0),
        },
        "all_candidates_count": 2,
        "source": "Static (Final)",
        "rivalry": {
            "leader": leader,
            "gap": abs(vote_gap),
            "gap_percent": abs(snapshot.get('percentage_gap', 0)),
            "pos2_party_id": snapshot.get('pos2_party_id', '10'),
            "pos3_party_id": snapshot.get('pos3_party_id', '35'),
        }
    }


def format_actas_progress(snapshot):
    """Format actas progress from snapshot."""
    region_code = snapshot['region_code']
    
    return {
        "region_code": region_code,
        "region_name": REGION_NAMES.get(region_code, region_code),
        "actas_percentage": snapshot.get('actas_percentage', 0),
        "actas_counted": snapshot.get('actas_counted', 0),
        "actas_total": snapshot.get('actas_total', 0),
        "participation": 0,
        "total_emitted_votes": snapshot.get('total_emitted_votes', 0),
        "total_valid_votes": snapshot.get('total_valid_votes', 0),
        "timestamp": snapshot.get('timestamp', ''),
    }


def format_history(snapshots):
    """Format history for /positions/history endpoint."""
    formatted = []
    for s in snapshots:
        formatted.append({
            "id": s.get('id', 0),
            "timestamp": s.get('timestamp', ''),
            "segundo": {
                "nombre": s.get('pos2_candidate_name', ''),
                "votos": s.get('pos2_votes', 0),
                "porcentaje": s.get('pos2_percentage', 0),
            },
            "tercero": {
                "nombre": s.get('pos3_candidate_name', ''),
                "votos": s.get('pos3_votes', 0),
                "porcentaje": s.get('pos3_percentage', 0),
            },
            "diferencia_votos": s.get('vote_gap', 0),
            "diferencia_porcentaje": s.get('percentage_gap', 0),
            "actas_porcentaje": s.get('actas_percentage', 0),
            "actas_contabilizadas": s.get('actas_counted', 0),
            "actas_total": s.get('actas_total', 0),
        })
    return {
        "hours": 168,
        "snapshots": formatted,
        "total": len(formatted),
    }


def format_regions(latest_by_region):
    """Format regions list."""
    regions = []
    
    for code in sorted(latest_by_region.keys()):
        name = REGION_NAMES.get(code, code)
        category = REGION_CATEGORIES.get(code, "departamento")
        regions.append({
            "code": code,
            "name": name,
            "category": category,
            "ubigeo": code if code not in ["TOTAL", "PERU", "EXTRANJERO", "NACIONAL"] else None,
        })
    
    # Sort: TOTAL first, then PERU, EXTRANJERO, then departments alphabetically
    priority = {"TOTAL": 0, "PERU": 1, "EXTRANJERO": 2}
    regions.sort(key=lambda x: (priority.get(x['code'], 99), x['name']))
    
    return {
        "regions": regions,
        "total_count": len(regions),
    }


def format_projection(snapshot):
    """Generate a static projection based on final data."""
    # Since it's the final result, projection equals current
    pos2_votes = snapshot.get('pos2_votes', 0)
    pos3_votes = snapshot.get('pos3_votes', 0)
    actas_pct = snapshot.get('actas_percentage', 0)
    
    leader = "juntos" if pos2_votes > pos3_votes else "renovacion"
    
    return {
        "actas_percentage": actas_pct,
        "confidence": "high",
        "snapshots_used": 100,
        "juntos": {
            "current_votes": pos2_votes,
            "projected_votes": pos2_votes,
            "projected_votes_low": pos2_votes,
            "projected_votes_high": pos2_votes,
            "growth_rate_per_pct": 0,
            "trend_direction": "stable",
        },
        "renovacion": {
            "current_votes": pos3_votes,
            "projected_votes": pos3_votes,
            "projected_votes_low": pos3_votes,
            "projected_votes_high": pos3_votes,
            "growth_rate_per_pct": 0,
            "trend_direction": "stable",
        },
        "projected_leader": leader,
        "current_leader": leader,
        "has_contradiction": False,
        "swap_probability": "unlikely",
        "methodology_text": "Resultados finales de la primera vuelta electoral.",
    }


def main():
    print("=" * 60)
    print("📦 EXPORTADOR DE DATOS ESTÁTICOS")
    print("=" * 60)
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Error: SUPABASE_URL y SUPABASE_KEY requeridas")
        sys.exit(1)
    
    print(f"\n🔗 Conectando a Supabase...")
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Create output directories
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "results"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "actas"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "history"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "projection"), exist_ok=True)
    
    print(f"📁 Output: {OUTPUT_DIR}\n")
    
    # Fetch data
    print("📥 FASE 1: Descargando datos de Supabase")
    latest_by_region = get_latest_snapshot_by_region(client)
    all_snapshots = get_all_snapshots_by_region(client)
    notifications = get_notifications(client)
    
    # Export data
    print("\n📤 FASE 2: Exportando JSONs")
    
    # 1. Regions list
    print("  💾 regions.json")
    regions_data = format_regions(latest_by_region)
    with open(os.path.join(OUTPUT_DIR, "regions.json"), "w") as f:
        json.dump(regions_data, f, indent=2)
    
    # 2. Live results per region
    print("  💾 results/*.json (live results por región)")
    for region_code, snapshot in latest_by_region.items():
        live_data = format_live_results(snapshot)
        filename = f"{region_code}.json"
        with open(os.path.join(OUTPUT_DIR, "results", filename), "w") as f:
            json.dump(live_data, f, indent=2)
    
    # 3. Actas progress per region
    print("  💾 actas/*.json (progreso de actas por región)")
    for region_code, snapshot in latest_by_region.items():
        actas_data = format_actas_progress(snapshot)
        filename = f"{region_code}.json"
        with open(os.path.join(OUTPUT_DIR, "actas", filename), "w") as f:
            json.dump(actas_data, f, indent=2)
    
    # 4. History per region
    print("  💾 history/*.json (historial por región)")
    for region_code, snapshots in all_snapshots.items():
        history_data = format_history(snapshots)
        filename = f"{region_code}.json"
        with open(os.path.join(OUTPUT_DIR, "history", filename), "w") as f:
            json.dump(history_data, f, indent=2)
    
    # 5. Projections per region
    print("  💾 projection/*.json (proyecciones por región)")
    for region_code, snapshot in latest_by_region.items():
        projection_data = format_projection(snapshot)
        filename = f"{region_code}.json"
        with open(os.path.join(OUTPUT_DIR, "projection", filename), "w") as f:
            json.dump(projection_data, f, indent=2)
    
    # 6. Notifications
    print("  💾 notifications.json")
    notifications_data = {
        "notifications": notifications,
        "count": len(notifications),
    }
    with open(os.path.join(OUTPUT_DIR, "notifications.json"), "w") as f:
        json.dump(notifications_data, f, indent=2)
    
    # 7. Metadata
    print("  💾 metadata.json")
    total_snapshot = latest_by_region.get("TOTAL", {})
    metadata = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "data_timestamp": total_snapshot.get("timestamp", ""),
        "total_regions": len(latest_by_region),
        "total_snapshots": sum(len(s) for s in all_snapshots.values()),
        "is_static": True,
        "election_phase": "Primera Vuelta - Resultados Finales",
        "actas_percentage": total_snapshot.get("actas_percentage", 0),
    }
    with open(os.path.join(OUTPUT_DIR, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ EXPORTACIÓN COMPLETADA")
    print("=" * 60)
    print(f"\n📁 Archivos en: {OUTPUT_DIR}")
    print(f"   • regions.json")
    print(f"   • results/{len(latest_by_region)} archivos")
    print(f"   • actas/{len(latest_by_region)} archivos")
    print(f"   • history/{len(all_snapshots)} archivos")
    print(f"   • projection/{len(latest_by_region)} archivos")
    print(f"   • notifications.json")
    print(f"   • metadata.json")
    
    print("\n📊 Resumen de datos:")
    print(f"   • Regiones: {len(latest_by_region)}")
    print(f"   • Snapshots totales: {sum(len(s) for s in all_snapshots.values())}")
    print(f"   • Notificaciones: {len(notifications)}")
    if total_snapshot:
        print(f"   • Actas procesadas: {total_snapshot.get('actas_percentage', 0):.1f}%")
        print(f"   • Último timestamp: {total_snapshot.get('timestamp', 'N/A')[:19]}")


if __name__ == "__main__":
    main()
