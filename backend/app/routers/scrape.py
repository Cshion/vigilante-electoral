"""
Scraping endpoint - Called by event bus/cron to populate DB.
Separado de los endpoints de lectura para mejor control.
"""
from datetime import datetime
from typing import Optional, List
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Header, Body, Response
from pydantic import BaseModel
from fastapi_cache import FastAPICache
import logging

from ..config import settings
from ..database import db
from ..services.scraper import scraper, REGIONS

logger = logging.getLogger(__name__)

PERU_TZ = ZoneInfo("America/Lima")

router = APIRouter(prefix="/api", tags=["scrape"])


class ScrapeRequest(BaseModel):
    """Request body for scrape endpoint."""
    regions: Optional[List[str]] = None  # null = all 27 regions


class RegionResult(BaseModel):
    """Result for a single region scrape."""
    region_code: str
    region_name: str
    success: bool
    changed: bool
    error: Optional[str] = None
    pos2_votes: Optional[int] = None
    pos3_votes: Optional[int] = None


class ScrapeResponse(BaseModel):
    """Response from scrape endpoint."""
    success: bool
    timestamp: str
    duration_seconds: float
    regions_scraped: int
    regions_changed: int
    regions_failed: int
    changes: List[RegionResult]
    errors: List[RegionResult]


@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_all(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_scrape_key: Optional[str] = Header(None, alias="X-Scrape-Key"),
    body: ScrapeRequest = Body(default=ScrapeRequest())
):
    """
    Scrape electoral data from ONPE and store in Supabase.
    
    Called by event bus/cron - NOT by frontend users.
    
    Authentication:
    - Bearer token via Authorization header (uses CRON_SECRET)
    - Or X-Scrape-Key header (uses SCRAPE_API_KEY)
    
    Body:
    - regions: List of region codes to scrape (null = all 27)
    
    Returns summary of what was scraped and what changed.
    """
    # Verify authorization
    authorized = False
    
    # Check Bearer token (CRON_SECRET)
    if settings.CRON_SECRET:
        if authorization and authorization == f"Bearer {settings.CRON_SECRET}":
            authorized = True
    
    # Check X-Scrape-Key header
    scrape_key = getattr(settings, 'SCRAPE_API_KEY', None)
    if scrape_key:
        if x_scrape_key and x_scrape_key == scrape_key:
            authorized = True
    
    # Allow if no secrets configured (dev mode)
    if not settings.CRON_SECRET and not scrape_key:
        authorized = True
    
    if not authorized:
        raise HTTPException(status_code=401, detail="Unauthorized - provide valid Authorization or X-Scrape-Key header")
    
    # Check DB connection
    if not db.is_connected:
        raise HTTPException(
            status_code=503,
            detail="Database not connected. Configure SUPABASE_URL and SUPABASE_KEY."
        )
    
    start_time = datetime.now(PERU_TZ)
    
    # Determine which regions to scrape
    if body.regions:
        # Validate provided region codes
        invalid_regions = [r for r in body.regions if r not in REGIONS]
        if invalid_regions:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown region codes: {invalid_regions}. Use /results/live/regions to see valid codes."
            )
        # Exclude NACIONAL alias to avoid duplicates with TOTAL
        regions_to_scrape = [r for r in body.regions if r != "NACIONAL"]
    else:
        # All regions EXCEPT NACIONAL alias (it's the same as TOTAL)
        regions_to_scrape = [r for r in REGIONS.keys() if r != "NACIONAL"]
    
    # Scrape all regions using the scraper service
    results = await scraper.scrape_all_regions(
        region_codes=regions_to_scrape
    )
    
    end_time = datetime.now(PERU_TZ)
    duration = (end_time - start_time).total_seconds()
    
    # Separate changed vs failed
    changes = [r for r in results if r["success"] and r["changed"]]
    errors = [r for r in results if not r["success"]]
    
    # Invalidate ALL cache when any region changes (fastapi-cache2 clears everything)
    if changes:
        try:
            await FastAPICache.clear()
            logger.info(f"Cache invalidated - {len(changes)} regions with new data")
        except Exception as e:
            logger.warning(f"Failed to clear cache: {e}")
    
    return ScrapeResponse(
        success=len(errors) == 0,
        timestamp=start_time.isoformat(),
        duration_seconds=round(duration, 2),
        regions_scraped=len(regions_to_scrape),
        regions_changed=len(changes),
        regions_failed=len(errors),
        changes=[RegionResult(**c) for c in changes],
        errors=[RegionResult(**e) for e in errors]
    )


@router.get("/scrape/status")
async def scrape_status(response: Response):
    """
    Get status of last scrapes across all regions.
    
    Returns when each region was last updated and its current vote counts.
    """
    # Never cache status/health endpoints
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    
    if not db.is_connected:
        raise HTTPException(
            status_code=503,
            detail="Database not connected."
        )
    
    status = []
    for region_code, region_info in REGIONS.items():
        latest = await db.get_latest_position_snapshot(region_code=region_code)
        
        if latest:
            status.append({
                "region_code": region_code,
                "region_name": region_info.get("name", region_code),
                "last_updated": latest.get("timestamp"),
                "pos2_votes": latest.get("pos2_votes"),
                "pos3_votes": latest.get("pos3_votes"),
                "pos2_candidate": latest.get("pos2_candidate_name"),
                "pos3_candidate": latest.get("pos3_candidate_name"),
            })
        else:
            status.append({
                "region_code": region_code,
                "region_name": region_info.get("name", region_code),
                "last_updated": None,
                "pos2_votes": None,
                "pos3_votes": None,
                "pos2_candidate": None,
                "pos3_candidate": None,
            })
    
    # Sort: NACIONAL first, EXTRANJERO second, then by name
    def sort_key(r):
        if r["region_code"] == "NACIONAL":
            return (0, "")
        if r["region_code"] == "EXTRANJERO":
            return (1, "")
        return (2, r["region_name"])
    
    return {
        "timestamp": datetime.now(PERU_TZ).isoformat(),
        "total_regions": len(REGIONS),
        "regions_with_data": len([s for s in status if s["last_updated"]]),
        "regions": sorted(status, key=sort_key)
    }


@router.get("/cache/stats")
async def cache_stats(response: Response):
    """
    Get in-memory cache statistics.
    
    Returns current cache state. Note: fastapi-cache2 InMemoryBackend
    doesn't expose detailed stats like the previous custom cache.
    """
    # Never cache status/health endpoints
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    
    backend = FastAPICache.get_backend()
    
    return {
        "timestamp": datetime.now(PERU_TZ).isoformat(),
        "backend": type(backend).__name__,
        "prefix": FastAPICache.get_prefix(),
        "status": "active" if backend else "not_initialized"
    }


@router.post("/cache/invalidate")
async def invalidate_all_cache(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_scrape_key: Optional[str] = Header(None, alias="X-Scrape-Key"),
):
    """
    Manually invalidate all cache entries.
    
    Requires same authentication as /api/scrape.
    """
    # Same auth check as scrape endpoint
    authorized = False
    
    if settings.CRON_SECRET:
        if authorization and authorization == f"Bearer {settings.CRON_SECRET}":
            authorized = True
    
    scrape_key = getattr(settings, 'SCRAPE_API_KEY', None)
    if scrape_key:
        if x_scrape_key and x_scrape_key == scrape_key:
            authorized = True
    
    if not settings.CRON_SECRET and not scrape_key:
        authorized = True
    
    if not authorized:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        await FastAPICache.clear()
        logger.info("Manual cache invalidation triggered")
        return {
            "success": True,
            "timestamp": datetime.now(PERU_TZ).isoformat(),
            "message": "All cache entries cleared"
        }
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {e}")
