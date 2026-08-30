"""Districts API — district-level training plans and platform metrics."""
from fastapi import APIRouter
from app.services.district_service import (
    get_district_plan,
    get_all_districts,
    get_platform_metrics_summary,
)

router = APIRouter()


@router.get("/districts")
async def list_districts():
    """Retrieve all Maharashtra districts with active telemetry."""
    return get_all_districts()


@router.get("/districts/metrics/summary")
async def district_platform_metrics():
    """Retrieve the 7 platform-level success metrics specified in Section 33."""
    return get_platform_metrics_summary()


@router.get("/districts/{name}/plan")
async def district_plan(name: str):
    """Retrieve 11-point comprehensive workforce action plan for a district."""
    return get_district_plan(name)

