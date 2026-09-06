"""Districts API — district-level training plans and platform metrics."""
import logging
from fastapi import APIRouter, HTTPException, status
from app.services.district_service import (
    get_district_plan,
    get_all_districts,
    get_platform_metrics_summary,
)

logger = logging.getLogger("skillsetu.districts")
router = APIRouter()


@router.get("/districts")
async def list_districts(is_demo: bool | None = None):
    """Retrieve all Maharashtra districts with active telemetry."""
    return get_all_districts(is_demo=is_demo)


@router.get("/districts/metrics/summary")
async def district_platform_metrics(is_demo: bool | None = None):
    """Retrieve the 7 platform-level success metrics specified in Section 33."""
    return get_platform_metrics_summary(is_demo=is_demo)


@router.get("/districts/{name}/plan")
async def district_plan(name: str, is_demo: bool | None = None):
    """Retrieve 11-point comprehensive workforce action plan for a district."""
    try:
        return get_district_plan(name, is_demo=is_demo)
    except Exception as e:
        logger.error("[DistrictPlan] Failed generating district plan for '%s': %s", name, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to generate district plan for '{name}' due to database or analytical service failure.",
        ) from e

