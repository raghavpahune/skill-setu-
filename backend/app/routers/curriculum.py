"""Curriculum API — course health audit, obsolescence detection, and syllabus modernization."""
import logging
from typing import Optional
from fastapi import APIRouter, Query, HTTPException, status
from app.services.curriculum_engine import (
    audit_all_courses,
    get_course_modernization_blueprint,
)

logger = logging.getLogger("skillsetu.curriculum")
router = APIRouter()


@router.get("/curriculum/audit")
async def get_curriculum_audit(
    district: Optional[str] = Query(None, description="Filter by district"),
    risk: Optional[str] = Query(None, description="Filter by obsolescence risk"),
    category: Optional[str] = Query(None, description="Filter by sector category"),
    is_demo: Optional[bool] = Query(None, description="Filter by demo/authoritative data source"),
):
    try:
        courses = audit_all_courses(is_demo=is_demo)
    except Exception as e:
        logger.error("[CurriculumAudit] Course audit failure: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to complete curriculum audit due to database or analytical service failure.",
        ) from e

    if district:
        d_clean = district.strip().lower()
        courses = [c for c in courses if d_clean in c.get("district", "").lower()]

    if risk:
        r_clean = risk.strip().upper()
        courses = [c for c in courses if c.get("obsolescence_risk") == r_clean]

    if category:
        c_clean = category.strip().lower()
        courses = [c for c in courses if c_clean in c.get("category", "").lower()]

    return {
        "status": "success",
        "total_courses_audited": len(courses),
        "courses": courses,
    }


@router.get("/curriculum/summary")
async def get_curriculum_summary(
    is_demo: Optional[bool] = Query(None, description="Filter by demo/authoritative data source"),
):
    try:
        courses = audit_all_courses(is_demo=is_demo)
    except Exception as e:
        logger.error("[CurriculumSummary] Course summary failure: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to compute curriculum summary due to database or analytical service failure.",
        ) from e
    total = len(courses)

    critical_obsolete = sum(1 for c in courses if c["obsolescence_risk"] == "CRITICAL_OBSOLETE")
    high_risk = sum(1 for c in courses if c["obsolescence_risk"] == "HIGH_RISK")
    oversupply_count = sum(1 for c in courses if "OVERSUPPLY" in c["oversupply_status"])
    avg_health = round(sum(c["health_score"] for c in courses) / max(1, total), 1)
    avg_modernity = round(sum(c["modernity_score"] for c in courses) / max(1, total), 1)
    total_equip_budget = sum(c["total_equipment_budget_inr"] for c in courses)

    return {
        "status": "success",
        "total_courses": total,
        "critical_obsolete_count": critical_obsolete,
        "high_risk_count": high_risk,
        "oversupply_count": oversupply_count,
        "avg_health_score": avg_health,
        "avg_modernity_score": avg_modernity,
        "total_equipment_budget_estimate_inr": total_equip_budget,
    }


@router.get("/curriculum/recommendations/{course_id}")
async def get_course_recommendations(
    course_id: str,
    is_demo: Optional[bool] = Query(None, description="Filter by demo/authoritative data source"),
):
    clean_course_id = course_id.strip()
    if not clean_course_id or len(clean_course_id) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid course ID format",
        )
    blueprint = get_course_modernization_blueprint(clean_course_id, is_demo=is_demo)
    if not blueprint:
        raise HTTPException(status_code=404, detail=f"Course '{clean_course_id}' not found")
    return blueprint
