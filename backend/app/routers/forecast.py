"""Skill Forecast API — future demand predictions and multi-horizon intelligence."""
from typing import Optional
from fastapi import APIRouter, Query
from app.services.forecast_engine import (
    compute_multi_horizon_forecasts,
    get_skill_forecast_trajectory,
    generate_future_skills_radar,
)

router = APIRouter()


@router.get("/forecast")
async def list_forecasts(
    horizon: Optional[str] = Query(None, description="Forecast horizon: 6m, 12m, 24m"),
    trend: Optional[str] = Query(None, description="Filter by trend: RISING, EMERGING, STABLE, DECLINING"),
    category: Optional[str] = Query(None, description="Filter by category"),
):
    """List skill forecasts with multi-horizon projections (backward compatible + extended)."""
    forecasts = compute_multi_horizon_forecasts()

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
async def future_skills_radar():
    """Return future skills radar matrix across rising, emerging, and stable clusters."""
    return generate_future_skills_radar()


@router.get("/forecast/skill/{skill_id}")
async def forecast_for_skill(skill_id: str):
    """Retrieve multi-horizon forecast trajectory for a specific skill."""
    trajectory = get_skill_forecast_trajectory(skill_id)
    if trajectory:
        return [trajectory]
    return []
