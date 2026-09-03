"""AI Copilot API — conversational assistant grounded in SkillSetu data."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


class CopilotQuery(BaseModel):
    question: str
    role: str = "student"  # government, institute, student, employer
    district: str | None = None
    student_id: str | None = None
    context_data: dict | None = None


class CareerExplainQuery(BaseModel):
    student_id: str = Field(..., description="Target candidate ID from student profiles or assessments")
    question: str | None = Field(default=None, description="Specific query or custom prompt")
    district: str | None = None


@router.post("/copilot/ask")
async def ask_copilot(query: CopilotQuery):
    """Conversational intelligence query grounded in Maharashtra labour datasets and candidate recommendations."""
    # ponytail: import here to avoid circular deps and keep startup fast
    from ai.copilot import handle_question
    answer = await handle_question(
        question=query.question,
        role=query.role,
        district=query.district,
        student_id=query.student_id,
        context_data=query.context_data,
    )
    return answer


@router.post("/copilot/explain-career")
async def explain_career(query: CareerExplainQuery):
    """Direct explainability endpoint for candidate career recommendations connecting assessments, validated employer demand, and schemes."""
    from ai.copilot import handle_question
    q = query.question or "Explain my career recommendations, skill gaps, and next learning roadmap steps."
    answer = await handle_question(
        question=q,
        role="student",
        district=query.district,
        student_id=query.student_id,
    )
    return answer

