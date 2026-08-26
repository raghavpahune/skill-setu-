"""AI Copilot API — conversational assistant grounded in SkillSetu data."""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class CopilotQuery(BaseModel):
    question: str
    role: str = "student"  # government, institute, student, employer


@router.post("/copilot/ask")
async def ask_copilot(query: CopilotQuery):
    # ponytail: import here to avoid circular deps and keep startup fast
    from ai.copilot import handle_question
    answer = await handle_question(query.question, query.role)
    return answer
