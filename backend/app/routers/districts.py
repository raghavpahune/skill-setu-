"""Districts API — district-level training plans."""
from fastapi import APIRouter
from app.services.district_service import get_district_plan, get_all_districts

router = APIRouter()


@router.get("/districts")
async def list_districts():
    return get_all_districts()


@router.get("/districts/{name}/plan")
async def district_plan(name: str):
    return get_district_plan(name)
