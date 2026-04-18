"""Endpoints para tracking de 2do y 3er puesto."""
from fastapi import APIRouter, HTTPException, Query
from fastapi_cache.decorator import cache
from typing import Optional
from datetime import datetime

from ..database import db
from ..services.scraper import scraper, REGIONS

router = APIRouter(prefix="/positions", tags=["positions"])


@router.get("/current", response_model=None)
@cache(expire=300)
async def get_current_race(
    region_code: str = Query("NACIONAL", description="Código de región (ej: 140000 para Lima)")
):
    """
    Obtener estado actual de la carrera entre 2do y 3er puesto.
    
    Lee los datos del último snapshot en Supabase (NO scrapea ONPE directamente).
    Los datos son actualizados por el cron job o POST /api/scrape.
    
    Retorna 404 si no hay datos para la región solicitada.
    """
    # Validar región
    if region_code not in REGIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Código de región desconocido: {region_code}. Usa /results/live/regions para ver códigos válidos."
        )
    
    try:
        # Obtener último snapshot de DB
        snapshot = await db.get_latest_position_snapshot(region_code=region_code)
        
        if not snapshot:
            raise HTTPException(
                status_code=404,
                detail=f"No hay datos disponibles para región {region_code}. "
                       f"Los datos aún no han sido scrapeados. "
                       f"Ejecuta POST /api/scrape o espera al cron job programado."
            )
        
        # Obtener el snapshot anterior para calcular cambios
        history = await db.get_position_history(hours=24, limit=2, region_code=region_code)
        
        vote_change_2 = None
        vote_change_3 = None
        gap_change = None
        position_swap = False
        minutes_since = None
        
        if len(history) > 1:
            prev_snapshot = history[1]
            vote_change_2 = snapshot["pos2_votes"] - prev_snapshot["pos2_votes"]
            vote_change_3 = snapshot["pos3_votes"] - prev_snapshot["pos3_votes"]
            current_gap = snapshot.get("vote_gap", snapshot["pos2_votes"] - snapshot["pos3_votes"])
            previous_gap = prev_snapshot.get("vote_gap", prev_snapshot["pos2_votes"] - prev_snapshot["pos3_votes"])
            gap_change = current_gap - previous_gap
            
            # Detectar swap
            position_swap = snapshot["pos2_candidate_id"] == prev_snapshot["pos3_candidate_id"]
        
        # Calcular minutos desde snapshot
        try:
            last_ts = datetime.fromisoformat(
                snapshot["timestamp"].replace("Z", "+00:00")
            )
            minutes_since = int((datetime.now(last_ts.tzinfo) - last_ts).total_seconds() / 60)
        except Exception:
            pass
        
        region_info = REGIONS.get(region_code, {})
        
        return {
            "timestamp": snapshot["timestamp"],
            "source": "Supabase",
            "region_code": region_code,
            "region_name": region_info.get("name", "Nacional"),
            
            # 1er puesto (referencia)
            "primero": {
                "nombre": snapshot.get("pos1_candidate_name"),
                "partido": None,  # No almacenamos partido de pos1
                "votos": snapshot.get("pos1_votes"),
                "porcentaje": snapshot.get("pos1_percentage"),
                "imagen": None
            },
            
            # 2do puesto
            "segundo": {
                "id": snapshot["pos2_candidate_id"],
                "nombre": snapshot["pos2_candidate_name"],
                "partido": snapshot["pos2_party_name"],
                "votos": snapshot["pos2_votes"],
                "porcentaje": snapshot["pos2_percentage"],
                "imagen": None,
                "cambio_votos": vote_change_2
            },
            
            # 3er puesto
            "tercero": {
                "id": snapshot["pos3_candidate_id"],
                "nombre": snapshot["pos3_candidate_name"],
                "partido": snapshot["pos3_party_name"],
                "votos": snapshot["pos3_votes"],
                "porcentaje": snapshot["pos3_percentage"],
                "imagen": None,
                "cambio_votos": vote_change_3
            },
            
            # Análisis de la carrera
            "carrera": {
                "diferencia_votos": snapshot.get("vote_gap", snapshot["pos2_votes"] - snapshot["pos3_votes"]),
                "diferencia_porcentaje": round(snapshot["pos2_percentage"] - snapshot["pos3_percentage"], 3),
                "cambio_brecha": gap_change,
                "hubo_cambio_posicion": position_swap,
                "minutos_desde_snapshot": minutes_since
            },
            
            # Totales
            "totales": {
                "votos_validos": snapshot.get("total_valid_votes"),
                "votos_emitidos": snapshot.get("total_emitted_votes"),
                "votos_blancos": snapshot.get("blank_votes"),
                "votos_nulos": snapshot.get("null_votes")
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/snapshot")
async def take_snapshot(
    force: bool = Query(False, description="Forzar snapshot sin esperar intervalo"),
    region_code: str = Query("NACIONAL", description="Código de región")
):
    """
    Tomar un snapshot del 2do y 3er puesto para una región específica.
    Por defecto solo toma si pasaron 15 min desde el último.
    """
    # Verificar conexión a DB
    if not db.is_connected:
        raise HTTPException(
            status_code=503,
            detail="Base de datos no configurada. Configura SUPABASE_URL y SUPABASE_KEY (service_role) en .env"
        )
    
    try:
        # Verificar intervalo (a menos que se fuerce)
        if not force:
            should_take = await db.should_take_snapshot(interval_minutes=15)
            if not should_take:
                last = await db.get_latest_position_snapshot(region_code=region_code)
                return {
                    "status": "skipped",
                    "message": "Aún no han pasado 15 minutos desde el último snapshot",
                    "region_code": region_code,
                    "last_snapshot": last["timestamp"] if last else None
                }
        
        # Obtener datos actuales de ONPE (regional si no es NACIONAL)
        if region_code == "NACIONAL":
            live_data = await scraper.scrape_presidential_results(top_n=3)
        else:
            live_data = await scraper.scrape_by_region(region_code, top_n=3, rivalry_only=False)
        
        if not live_data or len(live_data.get("candidates", [])) < 3:
            raise HTTPException(
                status_code=503,
                detail=f"No se pudieron obtener datos de ONPE para región {region_code}"
            )
        
        candidates = live_data["candidates"]
        totals = live_data.get("totals", {})
        
        pos1 = candidates[0]
        pos2 = candidates[1]
        pos3 = candidates[2]
        
        # Preparar datos para insertar
        snapshot_data = {
            "timestamp": live_data["timestamp"],
            
            "pos2": {
                "candidate_id": pos2["id"],
                "candidate_name": pos2["name"],
                "party_name": pos2["party_name"],
                "party_id": pos2.get("party_id"),
                "votes": pos2["votes"],
                "percentage": pos2["percentage"],
                "percentage_emitted": pos2.get("percentage_emitted")
            },
            
            "pos3": {
                "candidate_id": pos3["id"],
                "candidate_name": pos3["name"],
                "party_name": pos3["party_name"],
                "party_id": pos3.get("party_id"),
                "votes": pos3["votes"],
                "percentage": pos3["percentage"],
                "percentage_emitted": pos3.get("percentage_emitted")
            },
            
            "total_valid_votes": totals.get("valid_votes"),
            "total_emitted_votes": totals.get("emitted_votes"),
            "blank_votes": totals.get("blank_votes"),
            "null_votes": totals.get("null_votes"),
            
            "pos1_name": pos1["name"],
            "pos1_votes": pos1["votes"],
            "pos1_percentage": pos1["percentage"]
        }
        
        # Insertar en DB
        result = await db.insert_position_snapshot(snapshot_data, region_code=region_code)
        
        return {
            "status": "success",
            "message": "Snapshot guardado correctamente",
            "snapshot_id": result.get("id") if result else None,
            "region_code": region_code,
            "timestamp": live_data["timestamp"],
            "segundo": f"{pos2['name']} - {pos2['votes']:,} votos ({pos2['percentage']}%)",
            "tercero": f"{pos3['name']} - {pos3['votes']:,} votos ({pos3['percentage']}%)",
            "diferencia": f"{pos2['votes'] - pos3['votes']:,} votos"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
@cache(expire=300)
async def get_position_history(
    hours: int = Query(24, ge=1, le=168, description="Horas de historial"),
    limit: int = Query(100, ge=1, le=500),
    region_code: Optional[str] = Query(None, description="Código de región (ej: 140000 para Lima, NACIONAL, EXTRANJERO)")
):
    """
    Obtener historial de snapshots de posiciones.
    Si se especifica region_code, filtra por esa región.
    Si no se especifica, retorna historial de todas las regiones.
    """
    try:
        snapshots = await db.get_position_history(hours=hours, limit=limit, region_code=region_code)
        
        if not snapshots:
            return {
                "message": "No hay historial disponible",
                "snapshots": [],
                "total": 0,
                "region_code": region_code
            }
        
        # Formatear respuesta
        formatted = []
        for snap in snapshots:
            # Calculate blank and null percentages
            emitted = snap.get("total_emitted_votes") or 1  # Avoid division by zero
            blank_pct = ((snap.get("blank_votes") or 0) / emitted) * 100
            null_pct = ((snap.get("null_votes") or 0) / emitted) * 100
            
            formatted.append({
                "id": snap["id"],
                "timestamp": snap["timestamp"],
                "region_code": snap.get("region_code", "NACIONAL"),
                "segundo": {
                    "nombre": snap["pos2_candidate_name"],
                    "votos": snap["pos2_votes"],
                    "porcentaje": snap["pos2_percentage"]
                },
                "tercero": {
                    "nombre": snap["pos3_candidate_name"],
                    "votos": snap["pos3_votes"],
                    "porcentaje": snap["pos3_percentage"]
                },
                "diferencia_votos": snap["vote_gap"],
                "diferencia_porcentaje": snap["percentage_gap"],
                "blancos_porcentaje": round(blank_pct, 2),
                "nulos_porcentaje": round(null_pct, 2),
                # Actas progress
                "actas_porcentaje": snap.get("actas_percentage", 0),
                "actas_contabilizadas": snap.get("actas_counted", 0),
                "actas_total": snap.get("actas_total", 0),
            })
        
        return {
            "hours": hours,
            "region_code": region_code,
            "snapshots": formatted,
            "total": len(formatted)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/changes")
@cache(expire=300)
async def get_position_changes(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(50, ge=1, le=200)
):
    """Obtener historial de cambios entre snapshots."""
    try:
        changes = await db.get_position_changes(hours=hours, limit=limit)
        
        return {
            "hours": hours,
            "changes": changes,
            "total": len(changes),
            "swaps_detected": sum(1 for c in changes if c.get("position_swap"))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
