"""Skills API — master skill taxonomy."""
from fastapi import APIRouter
from app.db import get_demo

router = APIRouter()


@router.get("/skills")
async def list_skills():
    skills = get_demo("skills")
    job_skills = get_demo("job_skills")

    # Compute demand count per skill
    demand_counts = {}
    for js in job_skills:
        sid = js["skill_id"]
        demand_counts[sid] = demand_counts.get(sid, 0) + 1

    # Compute coverage per skill from course_skills
    course_skills = get_demo("course_skills")
    coverage = {}
    for cs in course_skills:
        sid = cs["skill_id"]
        lvl = cs.get("coverage_level", 0)
        if sid not in coverage or lvl > coverage[sid]:
            coverage[sid] = lvl

    result = []
    for s in skills:
        sid = s["id"]
        result.append({
            **s,
            "demand_count": demand_counts.get(sid, 0),
            "max_coverage_level": coverage.get(sid, 0),
        })

    result.sort(key=lambda x: x["demand_count"], reverse=True)
    return result


@router.get("/skills/{skill_id}")
async def get_skill(skill_id: str):
    skills = get_demo("skills")
    for s in skills:
        if s["id"] == skill_id:
            return s
    return {"error": "not found"}
