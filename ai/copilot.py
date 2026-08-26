"""AI Copilot orchestrator — selects provider, fetches context, returns grounded answer."""
import os
import sys
from pathlib import Path

# Ensure backend app is importable
_backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from ai.provider import LLMProvider
from ai.gemini_provider import GeminiProvider
from ai.demo_provider import DemoProvider


def _get_provider() -> LLMProvider:
    if os.getenv("GEMINI_API_KEY"):
        try:
            return GeminiProvider()
        except Exception:
            pass
    return DemoProvider()


def _build_context(role: str) -> dict:
    """Fetch relevant structured data to ground the response."""
    try:
        from app.db import get_demo
        from app.services.gap_engine import compute_gaps

        context = {
            "top_skill_gaps": compute_gaps()[:10],
            "total_skills_tracked": len(get_demo("skills")),
            "total_jobs": len(get_demo("jobs")),
        }

        if role == "student":
            context["student_profiles"] = [
                {"name": p["name"], "target_role": p["target_role"], "match": p["skill_match_pct"]}
                for p in get_demo("student_profiles")
            ]
        elif role == "government":
            from app.services.district_service import get_all_districts
            context["districts"] = get_all_districts()
        elif role == "employer":
            feedback = get_demo("employer_feedback")
            context["pending_validations"] = len([f for f in feedback if f["status"] == "pending"])
            context["confirmed"] = len([f for f in feedback if f["status"] == "confirmed"])

        return context
    except Exception:
        return {}


async def handle_question(question: str, role: str = "student") -> dict:
    """Handle a copilot question end-to-end."""
    provider = _get_provider()
    context = _build_context(role)

    try:
        answer = await provider.generate(question, context)
        return {
            "answer": answer,
            "role": role,
            "demo_mode": isinstance(provider, DemoProvider),
            "data_grounded": bool(context),
        }
    except Exception as e:
        # Ultimate fallback
        return {
            "answer": f"[Error] AI service unavailable — {str(e)}. Please check your GEMINI_API_KEY configuration.",
            "role": role,
            "demo_mode": True,
            "data_grounded": False,
        }
