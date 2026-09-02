"""Courses API — course health and recommendations."""
import logging
from fastapi import APIRouter, HTTPException, status
from app.db import get_demo
from app.repositories.supabase_repository import list_courses as list_courses_repo, SupabaseRepositoryError
from app.services.recommendation_service import get_curriculum_recommendations

logger = logging.getLogger("skillsetu.courses")
router = APIRouter()


@router.get("/courses")
async def list_courses():
    try:
        courses = list_courses_repo()
    except SupabaseRepositoryError as e:
        logger.error("[Courses] Failed fetching courses from Supabase: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed for courses: {e}",
        )

    placements = {p["course_id"]: p for p in get_demo("placements")}

    result = []
    for c in courses:
        p = placements.get(c.get("id"), {})
        student_count = c.get("student_count") or p.get("student_count", 0)
        placed_count = c.get("placed_count") or p.get("placed_count", 0)
        placement_rate = c.get("placement_rate") or (round(placed_count / student_count * 100) if student_count else 0)

        # Flag status
        status_flag = c.get("status") or "active"
        if status_flag == "active":
            if placement_rate < 30 and c.get("enrolment_count", 0) > 100:
                status_flag = "review_oversupply"
            elif placement_rate < 50:
                status_flag = "needs_attention"

        result.append({
            **c,
            "student_count": student_count,
            "placed_count": placed_count,
            "placement_rate": placement_rate,
            "status": status_flag,
        })

    return result


@router.get("/courses/recommendations")
async def course_recommendations():
    return get_curriculum_recommendations()
