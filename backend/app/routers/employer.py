"""Employer Validation & Industry Demand API — confirm/correct/reject skill demand, submit requirements, and track talent deficits."""
import datetime
import uuid
from collections import Counter
from fastapi import APIRouter, HTTPException, Query, status
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
    company_name: str | None = None
    employer_name: str | None = None
    industry: str = Field(..., min_length=2, max_length=150)
    district: str = Field(..., min_length=2, max_length=100)
    job_role: str | None = None
    role_title: str | None = None
    required_skills: list[str] | None = None
    skills: list[str] | None = None
    preferred_proficiency: str = "intermediate"
    proficiency_required: str | None = None
    openings_count: int | None = None
    positions_count: int | None = None
    experience_level: str = "Entry Level (0-1 yrs)"
    hiring_timeline: str = "Immediate (0-30 days)"
    urgency: str | None = None
    additional_requirements: str | None = None
    hiring_challenge: str | None = None
    nsqf_level: int = 5


class EmployerDemandSubmission(DemandSubmission):
    pass


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
@router.post("/employer/demands")
async def submit_demand(submission: EmployerDemandSubmission):
    """Submit new employer hiring requirements and skill demand signal into intelligence loop."""
    company = (submission.company_name or submission.employer_name or "").strip()
    role = (submission.job_role or submission.role_title or "").strip()
    skills_list = submission.required_skills or submission.skills or []

    if not company:
        raise HTTPException(status_code=422, detail="Company / Employer name is required.")
    if not role:
        raise HTTPException(status_code=422, detail="Target Job Role is required.")
    if not skills_list:
        raise HTTPException(status_code=422, detail="At least one required skill must be specified.")

    demand_id = f"ed-{uuid.uuid4().hex[:8]}"
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    now_date = datetime.date.today().isoformat()
    prof = submission.preferred_proficiency or submission.proficiency_required or "intermediate"
    openings = submission.positions_count if submission.positions_count is not None else (submission.openings_count or 1)
    timeline = submission.hiring_timeline or submission.urgency or "Immediate (0-30 days)"
    notes = submission.additional_requirements or submission.hiring_challenge


    demand_record = {
        "id": demand_id,
        "employer_id": submission.employer_id or f"emp-org-{uuid.uuid4().hex[:6]}",
        "company_name": company,
        "employer_name": company,
        "industry": submission.industry.strip(),
        "district": submission.district.strip(),
        "job_role": role,
        "role_title": role,
        "required_skills": skills_list,
        "skills": skills_list,
        "preferred_proficiency": prof,
        "proficiency_required": prof,
        "openings_count": max(1, openings),
        "positions_count": max(1, openings),
        "experience_level": submission.experience_level,
        "hiring_timeline": timeline,
        "urgency": timeline.lower().replace(" ", "_"),
        "additional_requirements": notes,
        "hiring_challenge": notes,
        "nsqf_level": submission.nsqf_level,
        "source": "EMPLOYER_SUBMITTED",
        "validation_status": "PENDING",
        "provenance_label": "Employer Submitted — Pending Validation",
        "is_demo": False,
        "submitted_at": now_iso,
        "submitted_date": now_date,
        "status": "pending",
    }

    saved = save_employer_demand(demand_record)
    return {
        "status": "created",
        "message": "Hiring requirement submitted for validation.",
        "demand": saved,
    }


@router.get("/employer/demands")
async def list_demands(
    district: str | None = None,
    industry: str | None = None,
    role: str | None = None,
    status: str | None = None,
    validation_status: str | None = None,
    source: str | None = None,
):
    """List employer-submitted skill demands with multi-parameter filtering."""
    demands = get_demo("employer_demands")
    results = demands

    if district and district.lower() != "all":
        d_clean = district.strip().lower()
        results = [d for d in results if d_clean in d.get("district", "").lower()]

    if industry and industry.lower() != "all":
        i_clean = industry.strip().lower()
        results = [d for d in results if i_clean in d.get("industry", "").lower()]

    if role and role.lower() != "all":
        r_clean = role.strip().lower()
        results = [
            d for d in results
            if r_clean in d.get("job_role", "").lower() or r_clean in d.get("role_title", "").lower()
        ]

    # Status / validation_status filter
    target_status = validation_status or status
    if target_status and target_status.lower() != "all":
        s_clean = target_status.strip().lower()
        results = [
            d for d in results
            if s_clean == d.get("validation_status", "").lower() or s_clean == d.get("status", "").lower()
        ]

    if source and source.lower() != "all":
        src_clean = source.strip().lower()
        results = [d for d in results if src_clean == d.get("source", "").lower()]

    return results


@router.get("/employer/demands/{demand_id}")
async def get_demand_detail(demand_id: str):
    """Retrieve detailed individual employer hiring demand record."""
    demands = get_demo("employer_demands")
    for d in demands:
        if d.get("id") == demand_id:
            return {"status": "success", "demand": d}

    raise HTTPException(status_code=404, detail=f"Employer demand '{demand_id}' not found.")


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

