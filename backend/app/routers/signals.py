"""Industry Signals API."""
from fastapi import APIRouter
from app.db import get_demo

router = APIRouter()


@router.get("/signals")
async def list_signals():
    signals = get_demo("industry_signals")
    skills_map = {s["id"]: s["name"] for s in get_demo("skills")}

    result = []
    for sig in signals:
        affected = [
            {"skill_id": sid, "skill_name": skills_map.get(sid, sid)}
            for sid in sig.get("affected_skills", [])
        ]
        result.append({
            "id": sig["id"],
            "title": sig["title"],
            "source": sig["source"],
            "technology": sig["technology"],
            "summary": sig["summary"],
            "impact_level": sig["impact_level"],
            "signal_date": sig["signal_date"],
            "affected_skills": affected,
        })

    result.sort(key=lambda x: x["signal_date"], reverse=True)
    return result


@router.get("/signals/{signal_id}")
async def get_signal(signal_id: str):
    signals = get_demo("industry_signals")
    for s in signals:
        if s["id"] == signal_id:
            return s
    return {"error": "not found"}
