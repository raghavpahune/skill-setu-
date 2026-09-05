"""Skill Forecast API — future demand predictions and multi-horizon intelligence."""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from app.services.forecast_engine import (
    compute_multi_horizon_forecasts,
    get_skill_forecast_trajectory,
    generate_future_skills_radar,
)
from app.repositories.supabase_repository import SupabaseRepositoryError

logger = logging.getLogger("skillsetu.forecast")

router = APIRouter()


@router.get("/forecast")
async def list_forecasts(
    horizon: Optional[str] = Query(None, description="Forecast horizon: 6m, 12m, 24m"),
    trend: Optional[str] = Query(None, description="Filter by trend: RISING, EMERGING, STABLE, DECLINING"),
    category: Optional[str] = Query(None, description="Filter by category"),
    is_demo: Optional[bool] = Query(None, description="Filter by demo/authoritative data source"),
):
    """List skill forecasts with multi-horizon projections (backward compatible + extended)."""
    try:
        forecasts = compute_multi_horizon_forecasts(is_demo=is_demo)
    except (SupabaseRepositoryError, Exception) as e:
        logger.exception("[ForecastAPI] Database query failed for forecasts: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database query failed for forecasts.",
        ) from e

    if trend:
        t_clean = trend.strip().upper()
        forecasts = [f for f in forecasts if f.get("trend") == t_clean]

    if category:
        c_clean = category.strip().lower()
        forecasts = [f for f in forecasts if c_clean in f.get("category", "").lower()]

    if horizon:
        h_clean = horizon.strip().lower()
        key_map = {"6m": "projected_6m", "12m": "projected_12m", "24m": "projected_24m"}
        sort_key = key_map.get(h_clean, "projected_24m")
        forecasts.sort(key=lambda x: x.get(sort_key, 0), reverse=True)

    return forecasts


@router.get("/forecast/radar")
async def future_skills_radar(is_demo: Optional[bool] = Query(None)):
    """Return future skills radar matrix across rising, emerging, and stable clusters."""
    try:
        return generate_future_skills_radar(is_demo=is_demo)
    except (SupabaseRepositoryError, Exception) as e:
        logger.exception("[ForecastAPI] Database query failed for future skills radar: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database query failed for future skills radar.",
        ) from e


@router.get("/forecast/skill/{skill_id}")
async def forecast_for_skill(
    skill_id: str,
    is_demo: Optional[bool] = Query(None, description="Filter by demo/authoritative data source"),
):
    """Retrieve multi-horizon forecast trajectory for a specific skill."""
    try:
        trajectory = get_skill_forecast_trajectory(skill_id, is_demo=is_demo)
    except (SupabaseRepositoryError, Exception) as e:
        logger.exception("[ForecastAPI] Database query failed for skill '%s': %s", skill_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database query failed for skill forecast trajectory.",
        ) from e

    if trajectory:
        return [trajectory]
    return []
