"""AI Copilot orchestrator — selects provider, fetches context, returns grounded answer."""
import os
import sys
import logging
from pathlib import Path

logger = logging.getLogger("skillsetu.ai.copilot")

# Ensure backend app is importable
_backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from ai.provider import LLMProvider
from ai.gemini_provider import GeminiProvider
from ai.demo_provider import DemoProvider


def _get_provider() -> LLMProvider:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        try:
            from app.config import settings
            api_key = settings.gemini_api_key or ""
        except Exception:
            pass

    if api_key and api_key.strip():
        try:
            prov = GeminiProvider()
            if prov.api_key:
                return prov
        except Exception as e:
            logger.error(f"[Copilot] GeminiProvider initialization failed: {e}")

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
    except Exception as e:
        logger.warning(f"[Copilot] Failed to build context: {e}")
        return {}


async def handle_question(question: str, role: str = "student") -> dict:
    """Handle a copilot question end-to-end."""
    provider = _get_provider()
    context = _build_context(role)
    is_live_ai = isinstance(provider, GeminiProvider)

    logger.info(f"[Copilot] Query: '{question}' (provider={provider.__class__.__name__}, is_live={is_live_ai}, role={role})")

    try:
        answer = await provider.generate(question, context)
        return {
            "answer": answer,
            "role": role,
            "demo_mode": not is_live_ai,
            "data_grounded": bool(context),
            "model": getattr(provider, "model", "gemini-2.0-flash"),
        }
    except Exception as e:
        err_msg = str(e)
        logger.error(f"[Copilot] Live generation error: {err_msg}")
        # Return the actual error message clearly so debugging is transparent
        return {
            "answer": f"[Gemini API Error] {err_msg}\n\nPlease check your Google AI Studio quota / API key permissions on Render.",
            "role": role,
            "demo_mode": True,
            "data_grounded": bool(context),
            "error_details": err_msg,
            "model": getattr(provider, "model", "unknown"),
        }
