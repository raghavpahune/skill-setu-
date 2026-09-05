"""Forecast Service — serves skill forecast data.

ponytail: At MVP this just returns stored demo data.
Upgrade path: plug in a real ML model (time series / trend analysis) here.
"""
from app.db import get_demo
from app.repositories.supabase_repository import list_skill_forecasts


def get_forecasts(skill_id: str | None = None, is_demo: bool | None = None) -> list[dict]:
    from app.core.data_mode import is_explicit_demo_mode
    if is_explicit_demo_mode(is_demo):
        skills_map = {s["id"]: s for s in get_demo("skills")}
        try:
            forecasts = list_skill_forecasts(skill_id=skill_id) or get_demo("skill_forecasts")
        except Exception:
            forecasts = get_demo("skill_forecasts")
    else:
        from app.repositories.supabase_repository import list_skills
        try:
            forecasts = list_skill_forecasts(skill_id=skill_id) or []
        except Exception:
            forecasts = []
        try:
            repo_skills = list_skills(limit=10000) or []
            skills_map = {s["id"]: s for s in repo_skills if "id" in s}
        except Exception:
            skills_map = {}

    return [
        {**f, "skill_name": skills_map.get(f.get("skill_id"), {}).get("name", "")}
        for f in forecasts
    ]
