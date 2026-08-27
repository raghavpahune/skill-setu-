"""Jobs API — labour market demand data."""
from collections import Counter
from fastapi import APIRouter, Query
from app.db import get_demo

router = APIRouter()


@router.get("/jobs")
async def list_jobs(
    district: str | None = None,
    industry: str | None = None,
    opportunity_type: str | None = None,
    limit: int = 50,
):
    jobs = get_demo("jobs")
    if district:
        jobs = [j for j in jobs if j["district"].lower() == district.lower()]
    if industry:
        jobs = [j for j in jobs if j["industry"].lower() == industry.lower()]
    if opportunity_type:
        jobs = [j for j in jobs if j.get("opportunity_type", "job").lower() == opportunity_type.lower()]
    return jobs[:limit]


@router.get("/jobs/demand")
async def job_demand(group_by: str = Query("district", enum=["district", "skill", "industry"])):
    """Aggregate job demand by district, skill, or industry."""
    jobs = get_demo("jobs")
    job_skills = get_demo("job_skills")
    skills = {s["id"]: s["name"] for s in get_demo("skills")}

    if group_by == "district":
        counts = Counter(j["district"] for j in jobs)
    elif group_by == "industry":
        counts = Counter(j["industry"] for j in jobs)
    elif group_by == "skill":
        counts = Counter(js["skill_id"] for js in job_skills)
        counts = {skills.get(k, k): v for k, v in counts.items()}
    else:
        counts = {}

    result = [{"name": k, "count": v} for k, v in counts.items()]
    result.sort(key=lambda x: x["count"], reverse=True)
    return result
