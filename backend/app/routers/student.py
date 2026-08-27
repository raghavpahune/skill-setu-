"""Student API — Skill Passport and learning roadmap."""
from fastapi import APIRouter
from app.db import get_demo

router = APIRouter()


@router.get("/student/{student_id}/passport")
async def skill_passport(student_id: str):
    profiles = get_demo("student_profiles")
    skills_map = {s["id"]: s for s in get_demo("skills")}

    for p in profiles:
        if p["user_id"] == student_id:
            current = [
                {
                    **sk,
                    "skill_name": skills_map.get(sk["skill_id"], {}).get("name", ""),
                    "category": skills_map.get(sk["skill_id"], {}).get("category", ""),
                    "nsqf_level": skills_map.get(sk["skill_id"], {}).get("nsqf_level"),
                }
                for sk in p.get("skills", [])
            ]
            required = [
                {
                    "skill_id": sid,
                    "skill_name": skills_map.get(sid, {}).get("name", ""),
                    "category": skills_map.get(sid, {}).get("category", ""),
                    "nsqf_level": skills_map.get(sid, {}).get("nsqf_level"),
                }
                for sid in p.get("required_skills", [])
            ]
            missing = [
                r for r in required
                if r["skill_id"] not in {s["skill_id"] for s in p.get("skills", [])}
            ]
            return {
                "user_id": p["user_id"],
                "name": p["name"],
                "target_role": p["target_role"],
                "skill_match_pct": p["skill_match_pct"],
                "current_skills": current,
                "required_skills": required,
                "missing_skills": missing,
            }

    return {"error": "student not found"}


@router.get("/student/{student_id}/roadmap")
async def learning_roadmap(student_id: str):
    profiles = get_demo("student_profiles")
    skills_map = {s["id"]: s for s in get_demo("skills")}
    forecasts = get_demo("skill_forecasts")

    forecast_map = {}
    for f in forecasts:
        if f["skill_id"] not in forecast_map:
            forecast_map[f["skill_id"]] = f

    for p in profiles:
        if p["user_id"] == student_id:
            roadmap = []
            for idx, sid in enumerate(p.get("roadmap", []), start=1):
                skill = skills_map.get(sid, {})
                fc = forecast_map.get(sid, {})
                roadmap.append({
                    "step": idx,
                    "skill_id": sid,
                    "skill_name": skill.get("name", ""),
                    "category": skill.get("category", ""),
                    "nsqf_level": skill.get("nsqf_level"),
                    "future_demand": fc.get("future_demand", "high"),
                    "trend": fc.get("trend", "rising"),
                    "confidence": fc.get("confidence", 85),
                    "timeframe": fc.get("timeframe", "2025-2027"),
                    "key_drivers": fc.get("key_drivers", []),
                    "why": f"Recommended because {skill.get('name', 'this skill')} has "
                           f"{fc.get('future_demand', 'growing')} future demand with "
                           f"{fc.get('trend', 'rising')} trend and {fc.get('confidence', '85')}% confidence.",
                })
            return {
                "user_id": p["user_id"],
                "target_role": p["target_role"],
                "roadmap": roadmap,
            }

    return {"error": "student not found"}


@router.get("/students")
async def list_students():
    """List all demo students (for role selector)."""
    profiles = get_demo("student_profiles")
    return [
        {"user_id": p["user_id"], "name": p["name"], "target_role": p["target_role"],
         "skill_match_pct": p["skill_match_pct"]}
        for p in profiles
    ]
