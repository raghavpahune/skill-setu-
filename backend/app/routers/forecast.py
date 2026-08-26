"""Skill Forecast API — future demand predictions."""
from fastapi import APIRouter
from app.db import get_demo

router = APIRouter()


@router.get("/forecast")
async def list_forecasts():
    forecasts = get_demo("skill_forecasts")
    skills_map = {s["id"]: s for s in get_demo("skills")}

    result = []
    for f in forecasts:
        skill = skills_map.get(f["skill_id"], {})
        result.append({
            **f,
            "skill_name": skill.get("name", "Unknown"),
            "category": skill.get("category", ""),
        })

    result.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    return result


@router.get("/forecast/skill/{skill_id}")
async def forecast_for_skill(skill_id: str):
    forecasts = get_demo("skill_forecasts")
    return [f for f in forecasts if f["skill_id"] == skill_id]
