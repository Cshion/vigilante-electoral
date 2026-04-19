"""Electoral results endpoints."""
from typing import Annotated
from fastapi import APIRouter, HTTPException, Query, Path
from fastapi_cache.decorator import cache

from ..database import db
from ..services.scraper import scraper, REGIONS
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/results", tags=["results"])


@router.get("/live")
@cache(expire=300)
async def get_live_results(
    top_n: int = Query(3, ge=1, le=20, description="Number of top candidates to return")
):
    """
    Get LIVE electoral results directly from ONPE API.
    No database required - fetches real-time data.
    """
    try:
        data = await scraper.scrape_presidential_results(top_n=top_n)
        
        if not data:
            raise HTTPException(
                status_code=503, 
                detail="Unable to fetch data from ONPE API. Service may be temporarily unavailable."
            )
        
        return {
            "election_type": data.get("election_type", "PRESI"),
            "timestamp": data.get("timestamp"),
            "candidates": data.get("candidates", []),
            "totals": data.get("totals", {}),
            "all_candidates_count": data.get("all_candidates_count", 0),
            "source": "ONPE API (live)"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Internal error in get_live_results")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/live/regions")
@cache(expire=3600)  # Static data - cache for 1 hour
async def list_available_regions():
    """
    List all available regions for electoral results.
    
    Categories:
    - total: TOTAL (Perú + Extranjero combined)
    - peru: PERU (National territory only)
    - extranjero: EXTRANJERO (Peruvians abroad)
    - departamento: Individual departments/regions
    """
    regions = []
    for code, data in REGIONS.items():
        # Skip NACIONAL alias (it's the same as TOTAL)
        if code == "NACIONAL":
            continue
            
        category = data.get("category", "departamento")
        regions.append({
            "code": code,
            "name": data["name"],
            "category": category,
            "ubigeo": data.get("ubigeo")
        })
    
    # Sort by category order, then alphabetically
    category_order = {"total": 0, "peru": 1, "extranjero": 2, "departamento": 3}
    
    def sort_key(r):
        return (category_order.get(r["category"], 99), r["name"])
    
    return {
        "regions": sorted(regions, key=sort_key),
        "total_count": len(regions),
        "categories": {
            "total": "Perú + Extranjero combinados",
            "peru": "Solo territorio nacional",
            "extranjero": "Peruanos en el exterior",
            "departamento": "Departamentos individuales"
        }
    }


@router.get("/live/actas/{region_code}")
@cache(expire=300)
async def get_actas_progress(
    region_code: Annotated[str, Path(description="Region code: NACIONAL, EXTRANJERO, or ubigeo (e.g., 140000 for Lima)")]
):
    """
    Get actas (ballot) counting progress for a specific region.
    
    Data is read from the database (populated by the scraper) to avoid direct ONPE calls.
    
    Returns:
    - actas_percentage: % of actas counted
    - actas_counted: number of actas counted
    - actas_total: total number of actas
    - region_code: the region code
    - region_name: human readable region name
    - timestamp: when the data was last scraped
    """
    # Validate region code
    if region_code not in REGIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown region code: {region_code}. Use /results/live/regions to see available codes."
        )
    
    try:
        data = await db.get_actas_progress(region_code)
        
        if not data:
            raise HTTPException(
                status_code=404,
                detail=f"No actas data available for region {region_code}. "
                       f"Data may not have been scraped yet. "
                       f"Trigger a scrape via POST /api/scrape or wait for the scheduled cron job."
            )
        
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Internal error in get_actas_progress")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/live/{region_code}")
@cache(expire=300)
async def get_live_results_by_region(
    region_code: Annotated[str, Path(description="Region code: NACIONAL, EXTRANJERO, or ubigeo (e.g., 140000 for Lima)")],
    top_n: Annotated[int, Query(ge=1, le=20, description="Number of top candidates to return")] = 3
):
    """
    Get electoral results for a specific region from database.
    
    Data is populated by the /api/scrape endpoint (called by cron/event bus).
    This endpoint only reads from Supabase - it does NOT call ONPE directly.
    
    Returns 404 if no data has been scraped for this region yet.
    """
    # Validate region code
    if region_code not in REGIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown region code: {region_code}. Use /results/live/regions to see available codes."
        )
    
    try:
        data = await db.get_latest_region_snapshot(region_code)
        
        if not data:
            raise HTTPException(
                status_code=404,
                detail=f"No data available for region {region_code}. Data may not have been scraped yet. "
                       f"Trigger a scrape via POST /api/scrape or wait for the scheduled cron job."
            )
        
        result = {
            "election_type": data.get("election_type", "PRESI"),
            "region_code": data.get("region_code"),
            "region_name": data.get("region_name"),
            "timestamp": data.get("timestamp"),
            "candidates": data.get("candidates", [])[:top_n] if top_n < len(data.get("candidates", [])) else data.get("candidates", []),
            "totals": data.get("totals", {}),
            "all_candidates_count": data.get("all_candidates_count", 0),
            "source": "Supabase",
        }
        
        # Include rivalry stats if present
        if data.get("rivalry"):
            result["rivalry"] = data["rivalry"]
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Internal error in get_live_results_by_region")
        raise HTTPException(status_code=500, detail="Internal server error")
