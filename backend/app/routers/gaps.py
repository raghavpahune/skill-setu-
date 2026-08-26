"""Skill Gaps API — demand vs. curriculum coverage."""
from fastapi import APIRouter
from app.db import get_demo
from app.services.gap_engine import compute_gaps

router = APIRouter()


@router.get("/gaps")
async def list_gaps():
    return compute_gaps()


@router.get("/gaps/district/{district}")
async def gaps_by_district(district: str):
    return compute_gaps(district=district)
