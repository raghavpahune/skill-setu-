"""Courses API — course health and recommendations."""
import logging
from fastapi import APIRouter, HTTPException, Query, status
from app.core.data_mode import is_explicit_demo_mode
from app.db import get_demo
from app.repositories.supabase_repository import list_courses as list_courses_repo, list_placements as list_placements_repo, SupabaseRepositoryError
from app.services.recommendation_service import get_curriculum_recommendations

logger = logging.getLogger("skillsetu.courses")
router = APIRouter()


@router.get("/courses")
async def list_courses(
    is_demo: bool | None = Query(None, description="Explicit demo/real mode selector"),
):
    if is_explicit_demo_mode(is_demo):
        courses = get_demo("courses")
        placements = {
            p["course_id"]: p
            for p in sorted(get_demo("placements"), key=lambda r: r.get("year") or 0)
            if p.get("course_id")
        }
    else:
        try:
            courses = list_courses_repo() or []
        except SupabaseRepositoryError as e:
            logger.exception("[Courses] Failed fetching courses from Supabase: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database query failed for courses.",
            ) from e
        try:
            repo_placements = list_placements_repo() or []
            placements = {
                p["course_id"]: p
                for p in sorted(repo_placements, key=lambda r: r.get("year") or 0)
                if p.get("course_id")
            }
        except Exception as e:
            logger.warning("[Courses] Could not fetch real placements: %s", e)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Placement data is temporarily unavailable.",
            ) from e

    result = []
    is_demo_mode = is_explicit_demo_mode(is_demo)
    for c in courses:
        cid = c.get("id")
        has_placement = (cid in placements) or (c.get("placement_rate") is not None) or (c.get("placed_count") is not None)
        p = placements.get(cid, {})
        student_count = c.get("student_count") or p.get("student_count")
        placed_count = c.get("placed_count") or p.get("placed_count")
        if c.get("placement_rate") is not None:
            placement_rate = c.get("placement_rate")
        elif student_count and placed_count is not None:
            placement_rate = round(placed_count / student_count * 100)
        else:
            placement_rate = 0 if is_demo_mode else None

        status_flag = c.get("status") or "active"
        if status_flag == "active" and has_placement and placement_rate is not None:
            if placement_rate < 30 and (c.get("enrolment_count") or 0) > 100:
                status_flag = "review_oversupply"
            elif placement_rate < 50:
                status_flag = "needs_attention"

        result.append({
            **c,
            "student_count": student_count or 0,
            "placed_count": placed_count or 0,
            "placement_rate": placement_rate if placement_rate is not None else 0,
            "status": status_flag,
        })

    return result


@router.get("/courses/recommendations")
async def course_recommendations(
    is_demo: bool | None = Query(None, description="Explicit demo/real mode selector"),
):
    return get_curriculum_recommendations(is_demo=is_demo)
