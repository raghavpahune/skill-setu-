"""Employer Validation & Industry Demand API — confirm/correct/reject skill demand, submit requirements, and track talent deficits."""
import datetime
import uuid
from collections import Counter
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from app.db import get_demo, save_employer_feedback, save_employer_demand

router = APIRouter()


class FeedbackSubmission(BaseModel):
    feedback_id: str
    status: str  # confirmed, corrected, rejected
    notes: str | None = None
    proficiency_required: str | None = None


class DemandSubmission(BaseModel):
    employer_id: str | None = None
    employer_name: str
    industry: str
    district: str
    role_title: str
    skills: list[str] = Field(default_factory=list)
    proficiency_required: str = "intermediate"  # beginner, intermediate, advanced
    nsqf_level: int = 5
    urgency: str = "immediate"  # immediate, next_quarter, future
    positions_count: int = 10
    hiring_challenge: str | None = None


@router.get("/employer/validate")
async def list_validations(
    status: str | None = None,
    district: str | None = None,
    industry: str | None = None,
    demand_level: str | None = None,
):
    """List skill demand summaries for employer validation with enriched metadata and filtering."""
    feedback = get_demo("employer_feedback")
    skills_map = {s["id"]: s for s in get_demo("skills")}
    employers_map = {e["id"]: e for e in get_demo("employers")}

    results = []
    for f in feedback:
        skill_info = skills_map.get(f.get("skill_id"), {})
        employer_info = employers_map.get(f.get("employer_id"), {})

        item = {
            **f,
            "skill_name": skill_info.get("name", "Unknown Skill"),
            "skill_category": skill_info.get("category", "General"),
            "nsqf_level": skill_info.get("nsqf_level", 5),
            "employer_name": employer_info.get("name", "Industry Partner"),
            "industry": employer_info.get("industry", "General Industry"),
            "district": employer_info.get("district", "Maharashtra"),
        }

        # Apply filters
        if status and status != "all" and item.get("status", "").lower() != status.lower():
            continue
        if district and district != "all" and item.get("district", "").lower() != district.lower():
            continue
        if industry and industry != "all" and item.get("industry", "").lower() != industry.lower():
            continue
        if demand_level and demand_level != "all" and item.get("demand_level", "").lower() != demand_level.lower():
            continue

        results.append(item)

    return results


@router.post("/employer/feedback")
async def submit_feedback(submission: FeedbackSubmission):
    """Submit employer validation (confirm/correct/reject) and persist to database."""
    updated = save_employer_feedback(
        feedback_id=submission.feedback_id,
        status=submission.status,
        notes=submission.notes,
        proficiency_required=submission.proficiency_required,
    )
    if updated:
        return {"status": "updated", "feedback": updated}
    return {"error": "feedback not found"}


@router.post("/employer/demand")
async def submit_demand(submission: DemandSubmission):
    """Submit new employer hiring requirements and skill demand signal into intelligence loop."""
    demand_id = f"ed-{uuid.uuid4().hex[:8]}"
    now_str = datetime.date.today().isoformat()

    demand_record = {
        "id": demand_id,
        "employer_id": submission.employer_id or f"emp-sub-{uuid.uuid4().hex[:6]}",
        "employer_name": submission.employer_name,
        "industry": submission.industry,
        "district": submission.district,
        "role_title": submission.role_title,
        "skills": submission.skills,
        "proficiency_required": submission.proficiency_required,
        "nsqf_level": submission.nsqf_level,
        "urgency": submission.urgency,
        "positions_count": max(1, submission.positions_count),
        "hiring_challenge": submission.hiring_challenge,
        "submitted_date": now_str,
        "status": "active",
    }

    saved = save_employer_demand(demand_record)
    return {"status": "created", "demand": saved}


@router.get("/employer/demands")
async def list_demands(
    district: str | None = None,
    industry: str | None = None,
    urgency: str | None = None,
):
    """List employer-submitted skill demands."""
    demands = get_demo("employer_demands")
    results = demands
    if district and district != "all":
        results = [d for d in results if d.get("district", "").lower() == district.lower()]
    if industry and industry != "all":
        results = [d for d in results if d.get("industry", "").lower() == industry.lower()]
    if urgency and urgency != "all":
        results = [d for d in results if d.get("urgency", "").lower() == urgency.lower()]
    return results


@router.get("/employer/difficult-skills")
async def list_difficult_skills():
    """Retrieve hard-to-hire skills telemetry, shortage indices, and intervention recommendations."""
    difficult = get_demo("difficult_skills")
    if not difficult:
        # Fallback dynamic calculation from gaps if table not loaded
        gaps = get_demo("skill_gaps")
        skills_map = {s["id"]: s["name"] for s in get_demo("skills")}
        difficult = [
            {
                "skill_id": g.get("skill_id", "sk-001"),
                "skill_name": skills_map.get(g.get("skill_id"), "Advanced Technology"),
                "deficit_score": int(g.get("gap_pct", 75)),
                "avg_days_to_fill": 45,
                "top_districts": ["Pune", "Mumbai"],
                "industries": ["Technology", "Manufacturing"],
                "shortage_reason": "High industry demand outpacing current academic pass-outs.",
                "hiring_challenge": "Candidate skills do not match modern production specifications.",
                "suggested_intervention": "Upgrade laboratory syllabus and sponsor faculty development programs.",
            }
            for g in gaps[:6]
        ]
    return difficult


@router.get("/employer/summary")
async def employer_summary():
    """Get high-level employer validation KPIs, approval rates, and industry participation."""
    feedback = get_demo("employer_feedback")
    demands = get_demo("employer_demands")
    employers = get_demo("employers")
    difficult = get_demo("difficult_skills")

    total_validations = len(feedback)
    confirmed_count = sum(1 for f in feedback if f.get("status") == "confirmed")
    pending_count = sum(1 for f in feedback if f.get("status") == "pending")
    corrected_count = sum(1 for f in feedback if f.get("status") == "corrected")
    rejected_count = sum(1 for f in feedback if f.get("status") == "rejected")

    reviewed_count = confirmed_count + corrected_count + rejected_count
    approval_rate = round((confirmed_count / max(1, reviewed_count)) * 100, 1) if reviewed_count > 0 else 0.0

    industry_counts = Counter(e.get("industry", "General") for e in employers)
    top_industries = [{"industry": k, "count": v} for k, v in industry_counts.most_common(6)]

    return {
        "total_validations": total_validations,
        "reviewed_count": reviewed_count,
        "confirmed_count": confirmed_count,
        "pending_count": pending_count,
        "corrected_count": corrected_count,
        "rejected_count": rejected_count,
        "approval_rate": approval_rate,
        "active_employers_count": len(employers),
        "active_demands_count": len(demands),
        "hard_to_hire_count": len(difficult),
        "top_industries": top_industries,
    }

