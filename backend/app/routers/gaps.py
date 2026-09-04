"""Skill Gaps API — demand vs. curriculum coverage."""
from fastapi import APIRouter
from app.db import get_demo
from app.services.gap_engine import compute_gaps

router = APIRouter()


@router.get("/gaps")
async def list_gaps(is_demo: bool | None = None):
    return compute_gaps(is_demo=is_demo)


@router.get("/gaps/district/{district}")
async def gaps_by_district(district: str, is_demo: bool | None = None):
    return compute_gaps(district=district, is_demo=is_demo)
