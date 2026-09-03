"""Forecast Service — serves skill forecast data.

ponytail: At MVP this just returns stored demo data.
Upgrade path: plug in a real ML model (time series / trend analysis) here.
"""
from app.db import get_demo
from app.repositories.supabase_repository import list_skill_forecasts


def get_forecasts(skill_id: str | None = None) -> list[dict]:
    forecasts = list_skill_forecasts(skill_id=skill_id)
    skills_map = {s["id"]: s for s in get_demo("skills")}

    return [
        {**f, "skill_name": skills_map.get(f.get("skill_id"), {}).get("name", "")}
        for f in forecasts
    ]
