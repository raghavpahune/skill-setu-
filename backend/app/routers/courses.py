"""Courses API — course health and recommendations."""
from fastapi import APIRouter
from app.db import get_demo
from app.services.recommendation_service import get_curriculum_recommendations

router = APIRouter()


@router.get("/courses")
async def list_courses():
    courses = get_demo("courses")
    placements = {p["course_id"]: p for p in get_demo("placements")}

    result = []
    for c in courses:
        p = placements.get(c["id"], {})
        student_count = p.get("student_count", 0)
        placed_count = p.get("placed_count", 0)
        placement_rate = round(placed_count / student_count * 100) if student_count else 0

        # Flag status
        status = "active"
        if placement_rate < 30 and c.get("enrolment_count", 0) > 100:
            status = "review_oversupply"
        elif placement_rate < 50:
            status = "needs_attention"

        result.append({
            **c,
            "student_count": student_count,
            "placed_count": placed_count,
            "placement_rate": placement_rate,
            "status": status,
        })

    return result


@router.get("/courses/recommendations")
async def course_recommendations():
    return get_curriculum_recommendations()
