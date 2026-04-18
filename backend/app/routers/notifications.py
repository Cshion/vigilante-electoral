"""
Notifications router - Get change notifications for regions.

SIMPLIFIED: No per-user read tracking since notifications are SHARED.
- Caching handled by fastapi-cache2
- Returns recent changes (last 24h)
- Only change when scraper runs (every 15 min)
"""
from typing import Annotated, List, Optional
from fastapi import APIRouter, Query
from fastapi_cache.decorator import cache
from pydantic import BaseModel
from datetime import datetime

from ..database import db

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class Notification(BaseModel):
    """Notification model for API responses."""
    id: int
    region_code: str
    region_name: str
    timestamp: datetime
    notification_type: str
    leader: str
    juntos_votes: int
    juntos_change: int
    renovacion_votes: int
    renovacion_change: int
    gap: int
    gap_change: int
    actas_percentage: Optional[float] = None
    message: str


class NotificationsResponse(BaseModel):
    """Response model for notifications list."""
    notifications: List[Notification]
    count: int


@router.get("", response_model=NotificationsResponse)
@cache(expire=300)
async def get_notifications(
    limit: Annotated[int, Query(ge=1, le=100, description="Max notifications to return")] = 50,
    hours: Annotated[int, Query(ge=1, le=168, description="Hours of history")] = 24,
):
    """
    Get change notifications for regions.
    
    Notifications are generated when votes change in any region
    except TOTAL (which is always visible on the main page).
    
    Notifications are shared between all users.
    
    Returns notifications sorted by timestamp (newest first).
    """
    notifications = await db.get_notifications(
        limit=limit,
        hours=hours,
    )
    
    return NotificationsResponse(
        notifications=[Notification(**n) for n in notifications],
        count=len(notifications),
    )
