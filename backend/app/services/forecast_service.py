"""Forecast Service — serves skill forecast data.

ponytail: At MVP this just returns stored demo data.
Upgrade path: plug in a real ML model (time series / trend analysis) here.
"""
from app.db import get_demo


def get_forecasts(skill_id: str | None = None) -> list[dict]:
    forecasts = get_demo("skill_forecasts")
    skills_map = {s["id"]: s for s in get_demo("skills")}

    if skill_id:
        forecasts = [f for f in forecasts if f["skill_id"] == skill_id]

    return [
        {**f, "skill_name": skills_map.get(f["skill_id"], {}).get("name", "")}
        for f in forecasts
    ]
