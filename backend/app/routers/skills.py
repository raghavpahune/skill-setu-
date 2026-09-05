"""Skills API — master skill taxonomy."""
from fastapi import APIRouter, Query
from app.core.data_mode import is_explicit_demo_mode
from app.db import get_demo

router = APIRouter()


@router.get("/skills")
async def list_skills(
    is_demo: bool | None = Query(None, description="Explicit demo/real mode selector"),
):
    if is_explicit_demo_mode(is_demo):
        skills = get_demo("skills")
        job_skills = get_demo("job_skills")
        course_skills = get_demo("course_skills")
    else:
        try:
            from app.repositories import supabase_repository
            skills = supabase_repository.list_skills(limit=1000) or []
            jobs = supabase_repository.list_jobs(limit=1000) or []
            job_ids = [j.get("id") for j in jobs if j.get("id")]
            job_skills = supabase_repository.list_job_skills(job_ids=job_ids) if job_ids else []
            courses = supabase_repository.list_courses(limit=1000) or []
            course_ids = [c.get("id") for c in courses if c.get("id")]
            course_skills = supabase_repository.list_course_skills(course_ids=course_ids) if course_ids else []
        except Exception:
            skills = []
            job_skills = []
            course_skills = []

    # Compute demand count per skill
    demand_counts = {}
    for js in job_skills:
        sid = js.get("skill_id")
        if sid:
            demand_counts[sid] = demand_counts.get(sid, 0) + 1

    # Compute coverage per skill from course_skills
    coverage = {}
    for cs in course_skills:
        sid = cs.get("skill_id")
        if sid:
            lvl = cs.get("coverage_level", 0)
            if sid not in coverage or lvl > coverage[sid]:
                coverage[sid] = lvl

    result = []
    for s in skills:
        sid = s.get("id")
        result.append({
            **s,
            "demand_count": demand_counts.get(sid, 0),
            "max_coverage_level": coverage.get(sid, 0),
        })

    result.sort(key=lambda x: x["demand_count"], reverse=True)
    return result


@router.get("/skills/{skill_id}")
async def get_skill(
    skill_id: str,
    is_demo: bool | None = Query(None, description="Explicit demo/real mode selector"),
):
    if is_explicit_demo_mode(is_demo):
        skills = get_demo("skills")
        for s in skills:
            if s.get("id") == skill_id:
                return s
    else:
        try:
            from app.repositories import supabase_repository
            skills = supabase_repository.list_skills(limit=1000) or []
            for s in skills:
                if s.get("id") == skill_id:
                    return s
        except Exception:
            pass
    return {"error": "not found"}
