import logging
from collections import Counter
from fastapi import APIRouter, Query
from app.core.data_mode import is_explicit_demo_mode
from app.db import get_demo

logger = logging.getLogger("skillsetu.routers.jobs")
router = APIRouter()


@router.get("/jobs")
async def list_jobs(
    district: str | None = None,
    industry: str | None = None,
    opportunity_type: str | None = None,
    limit: int = 50,
    is_demo: bool | None = Query(None, description="Explicit demo/real mode selector"),
):
    if is_explicit_demo_mode(is_demo):
        jobs = get_demo("jobs")
        if district:
            jobs = [j for j in jobs if j["district"].lower() == district.lower()]
        if industry:
            jobs = [j for j in jobs if j["industry"].lower() == industry.lower()]
        if opportunity_type:
            jobs = [j for j in jobs if j.get("opportunity_type", "job").lower() == opportunity_type.lower()]
        return jobs[:limit]

    # Real mode: query authoritative repository ONLY
    try:
        from app.repositories.supabase_repository import list_jobs as list_jobs_repo
        repo_jobs = list_jobs_repo(district=district, industry=industry, opportunity_type=opportunity_type, limit=limit)
        return repo_jobs or []
    except Exception as exc:
        logger.warning("[Jobs API] Authoritative repository lookup failed: %s", exc)
        return []


@router.get("/jobs/demand")
async def job_demand(
    group_by: str = Query("district", enum=["district", "skill", "industry"]),
    is_demo: bool | None = Query(None, description="Explicit demo/real mode selector"),
):
    """Aggregate job demand by district, skill, or industry."""
    if is_explicit_demo_mode(is_demo):
        jobs = get_demo("jobs")
        job_skills = get_demo("job_skills")
        skills = {s["id"]: s["name"] for s in get_demo("skills")}
    else:
        try:
            from app.repositories.supabase_repository import list_jobs as list_jobs_repo, list_job_skills, list_skills
            jobs = list_jobs_repo(limit=1000) or []
            job_ids = [j.get("id") for j in jobs if j.get("id")]
            job_skills = list_job_skills(job_ids=job_ids) if job_ids else []
            skills = {s["id"]: s.get("name", s["id"]) for s in (list_skills(limit=1000) or [])}
        except Exception as exc:
            logger.warning("[Jobs API] Authoritative lookup for job_demand failed: %s", exc)
            jobs = []
            job_skills = []
            skills = {}

    if group_by == "district":
        counts = Counter(j["district"] for j in jobs if j.get("district"))
    elif group_by == "industry":
        counts = Counter(j["industry"] for j in jobs if j.get("industry"))
    elif group_by == "skill":
        counts = Counter(js["skill_id"] for js in job_skills if js.get("skill_id"))
        counts = {skills.get(k, k): v for k, v in counts.items()}
    else:
        counts = {}

    result = [{"name": k, "count": v} for k, v in counts.items()]
    result.sort(key=lambda x: x["count"], reverse=True)
    return result
