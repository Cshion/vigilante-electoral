"""Endpoints para tracking de 2do y 3er puesto."""
from fastapi import APIRouter, HTTPException, Query
from fastapi_cache.decorator import cache
from typing import Annotated, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import math

from ..database import db
from ..services.scraper import scraper, REGIONS
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Models para Proyección
# =============================================================================

class ProjectionCandidate(BaseModel):
    """Datos de proyección para un candidato."""
    party_name: str
    current_votes: int
    projected_votes: int
    projected_votes_low: int
    projected_votes_high: int
    growth_rate_per_pct: float = Field(description="Votos ganados por cada 1% de actas")
    trend_direction: str = Field(description="increasing, decreasing, stable")


class ProjectionResponse(BaseModel):
    """Respuesta del endpoint de proyección."""
    timestamp: str
    region_code: str
    region_name: str
    actas_percentage: float
    remaining_actas_pct: float
    snapshots_used: int
    confidence: str = Field(description="high, medium, low, insufficient")
    juntos: ProjectionCandidate
    renovacion: ProjectionCandidate
    projected_leader: str
    current_leader: str
    projected_gap: int
    has_contradiction: bool
    swap_probability: str = Field(description="unlikely, possible, likely")
    methodology_text: str

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
        logger.exception("Internal error in get_current_race")
        raise HTTPException(status_code=500, detail="Internal server error")


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
        logger.exception("Internal error in take_snapshot")
        raise HTTPException(status_code=500, detail="Internal server error")


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
        logger.exception("Internal error in get_position_history")
        raise HTTPException(status_code=500, detail="Internal server error")


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
        logger.exception("Internal error in get_position_changes")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/projection", response_model=ProjectionResponse)
@cache(expire=300)  # Cache 5 minutos
async def get_vote_projection(
    region_code: Annotated[str, Query(description="Código de región")] = "TOTAL"
):
    """
    Proyección de votos finales usando tendencia histórica (TBP Algorithm).
    
    Usa TODOS los snapshots disponibles para calcular la tasa de crecimiento
    de votos por cada 1% de actas procesadas, con peso exponencial decreciente
    (más peso a datos recientes).
    
    SIEMPRE muestra proyección — no hay límite de % de actas.
    """
    # Validar región
    if region_code not in REGIONS:
        raise HTTPException(status_code=400, detail=f"Región desconocida: {region_code}")
    
    # Obtener TODOS los snapshots (sin límite de tiempo)
    snapshots = await db.get_all_position_snapshots_for_projection(region_code)
    
    if len(snapshots) < 3:
        raise HTTPException(
            status_code=404, 
            detail=f"Datos insuficientes para proyectar ({len(snapshots)} snapshots). Se necesitan al menos 3."
        )
    
    current = snapshots[0]
    actas_pct = current.get("actas_percentage", 0) or 0
    remaining_actas = 100 - actas_pct
    
    # Calcular deltas entre snapshots consecutivos
    deltas = []
    for i in range(len(snapshots) - 1):
        curr = snapshots[i]
        prev = snapshots[i + 1]
        
        delta_actas = (curr.get("actas_percentage", 0) or 0) - (prev.get("actas_percentage", 0) or 0)
        
        if delta_actas <= 0.001:  # Skip si no hubo avance significativo
            continue
        
        deltas.append({
            "pos2_rate": (curr["pos2_votes"] - prev["pos2_votes"]) / delta_actas,
            "pos3_rate": (curr["pos3_votes"] - prev["pos3_votes"]) / delta_actas,
            "actas_delta": delta_actas
        })
    
    if len(deltas) < 2:
        raise HTTPException(
            status_code=404, 
            detail="No hay suficientes cambios de actas para proyectar"
        )
    
    # Calcular promedio ponderado exponencial (EWA)
    decay = 0.8  # Factor de decaimiento
    
    def weighted_stats(rates: list) -> tuple:
        """Calcular media y desviación estándar ponderadas exponencialmente."""
        weights = [decay ** i for i in range(len(rates))]
        total_weight = sum(weights)
        mean = sum(r * w for r, w in zip(rates, weights)) / total_weight
        variance = sum(w * (r - mean)**2 for r, w in zip(rates, weights)) / total_weight
        std_dev = math.sqrt(variance)
        return mean, std_dev
    
    pos2_rates = [d["pos2_rate"] for d in deltas]
    pos3_rates = [d["pos3_rate"] for d in deltas]
    
    pos2_growth, pos2_std = weighted_stats(pos2_rates)
    pos3_growth, pos3_std = weighted_stats(pos3_rates)
    
    # Proyectar votos finales
    pos2_projected = int(current["pos2_votes"] + pos2_growth * remaining_actas)
    pos2_low = int(current["pos2_votes"] + (pos2_growth - 1.5 * pos2_std) * remaining_actas)
    pos2_high = int(current["pos2_votes"] + (pos2_growth + 1.5 * pos2_std) * remaining_actas)
    
    pos3_projected = int(current["pos3_votes"] + pos3_growth * remaining_actas)
    pos3_low = int(current["pos3_votes"] + (pos3_growth - 1.5 * pos3_std) * remaining_actas)
    pos3_high = int(current["pos3_votes"] + (pos3_growth + 1.5 * pos3_std) * remaining_actas)
    
    # Detectar tendencia (comparar últimos 3 vs resto)
    def detect_trend(rates: list) -> str:
        """Detectar si la tendencia es creciente, decreciente o estable."""
        if len(rates) < 4:
            return "stable"
        recent = sum(rates[:3]) / 3
        older = sum(rates[3:]) / len(rates[3:])
        momentum = (recent - older) / max(abs(older), 1)
        if momentum > 0.05:
            return "increasing"
        elif momentum < -0.05:
            return "decreasing"
        return "stable"
    
    # Calcular confianza
    def calc_confidence(actas_pct: float, sample_count: int, rel_std: float) -> str:
        """Calcular nivel de confianza de la proyección."""
        if sample_count < 3:
            return "insufficient"
        if actas_pct > 85:
            return "high"
        if actas_pct > 60 and rel_std < 0.15:
            return "high"
        if actas_pct > 40:
            return "medium"
        return "low"
    
    avg_std = (pos2_std + pos3_std) / 2
    avg_growth = (abs(pos2_growth) + abs(pos3_growth)) / 2
    rel_std = avg_std / max(avg_growth, 1)
    confidence = calc_confidence(actas_pct, len(deltas), rel_std)
    
    # Análisis de carrera
    current_leader = "POS2" if current["pos2_votes"] > current["pos3_votes"] else "POS3"
    projected_leader = "POS2" if pos2_projected > pos3_projected else "POS3"
    has_contradiction = current_leader != projected_leader
    
    projected_gap = pos2_projected - pos3_projected
    
    # Probabilidad de swap
    swap_prob = "unlikely"
    if pos2_low < pos3_high and pos3_low < pos2_high:
        swap_prob = "possible"
        if abs(projected_gap) < (pos2_std + pos3_std) * remaining_actas * 0.5:
            swap_prob = "likely"
    
    region_info = REGIONS.get(region_code, {})
    
    return ProjectionResponse(
        timestamp=current.get("timestamp", datetime.now().isoformat()),
        region_code=region_code,
        region_name=region_info.get("name", region_code),
        actas_percentage=round(actas_pct, 2),
        remaining_actas_pct=round(remaining_actas, 2),
        snapshots_used=len(deltas),
        confidence=confidence,
        juntos=ProjectionCandidate(
            party_name=current.get("pos2_party_name", "JUNTOS POR EL PERÚ"),
            current_votes=current["pos2_votes"],
            projected_votes=pos2_projected,
            projected_votes_low=pos2_low,
            projected_votes_high=pos2_high,
            growth_rate_per_pct=round(pos2_growth, 0),
            trend_direction=detect_trend(pos2_rates)
        ),
        renovacion=ProjectionCandidate(
            party_name=current.get("pos3_party_name", "RENOVACIÓN POPULAR"),
            current_votes=current["pos3_votes"],
            projected_votes=pos3_projected,
            projected_votes_low=pos3_low,
            projected_votes_high=pos3_high,
            growth_rate_per_pct=round(pos3_growth, 0),
            trend_direction=detect_trend(pos3_rates)
        ),
        projected_leader="JUNTOS" if projected_leader == "POS2" else "RENOVACIÓN",
        current_leader="JUNTOS" if current_leader == "POS2" else "RENOVACIÓN",
        projected_gap=projected_gap,
        has_contradiction=has_contradiction,
        swap_probability=swap_prob,
        methodology_text=(
            f"Proyección basada en {len(deltas)} cambios históricos. "
            f"Tasa de crecimiento: JUNTOS +{int(pos2_growth):,}/1% actas, "
            f"RENOVACIÓN +{int(pos3_growth):,}/1% actas. "
            f"Confianza: {confidence}."
        )
    )
