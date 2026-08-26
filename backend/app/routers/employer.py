"""Employer Validation API — confirm/correct/reject skill demand."""
from fastapi import APIRouter
from pydantic import BaseModel
from app.db import get_demo

router = APIRouter()


class FeedbackSubmission(BaseModel):
    feedback_id: str
    status: str  # confirmed, corrected, rejected
    notes: str | None = None
    proficiency_required: str | None = None


@router.get("/employer/validate")
async def list_validations():
    """List skill demand summaries for employer validation."""
    feedback = get_demo("employer_feedback")
    skills_map = {s["id"]: s["name"] for s in get_demo("skills")}
    employers_map = {e["id"]: e["name"] for e in get_demo("employers")}

    return [
        {
            **f,
            "skill_name": skills_map.get(f["skill_id"], "Unknown"),
            "employer_name": employers_map.get(f["employer_id"], "Unknown"),
        }
        for f in feedback
    ]


@router.post("/employer/feedback")
async def submit_feedback(submission: FeedbackSubmission):
    """Submit employer validation (confirm/correct/reject)."""
    feedback = get_demo("employer_feedback")
    for f in feedback:
        if f["id"] == submission.feedback_id:
            f["status"] = submission.status
            if submission.notes:
                f["notes"] = submission.notes
            if submission.proficiency_required:
                f["proficiency_required"] = submission.proficiency_required
            return {"status": "updated", "feedback": f}
    return {"error": "feedback not found"}
