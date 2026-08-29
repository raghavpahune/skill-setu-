"""Student API — Skill Passport, learning roadmap, personalized industry alerts, skill explainability, and student self-assessment."""
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field
from app.db import get_demo, save_student_assessment
from app.services.student_service import (
    list_alert_domains,
    get_personalized_industry_alerts,
    get_skill_explainability,
    get_diagnostic_quiz_questions,
    evaluate_student_assessment,
)

router = APIRouter()


class SkillProficiencyInput(BaseModel):
    skill_name: str = Field(..., min_length=1, max_length=100)
    proficiency: str = Field(default="intermediate", description="beginner, intermediate, advanced")


class AssessmentSubmission(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Candidate full name")
    education: str = Field(..., min_length=2, max_length=150, description="Current course, degree, or ITI trade")
    career_goal: str = Field(..., min_length=2, max_length=100, description="Desired target career role")
    current_skills: list[SkillProficiencyInput] = Field(default_factory=list, description="Self-assessed skills")
    interests: list[str] = Field(default_factory=list, description="Domains of interest")
    quiz_answers: dict[str, str] = Field(default_factory=dict, description="Key-value mapping of question ID to chosen option key")
    district: str | None = Field(default="Maharashtra", description="District in Maharashtra")


@router.get("/student/alert-domains")
async def alert_domains():
    """Return all supported industry alert domains for student interest filtering."""
    return {"domains": list_alert_domains()}


@router.get("/student/industry-alerts")
async def student_industry_alerts(
    domain: str | None = Query(None, description="Domain key (ai_ml, cloud, ev, etc.) or 'all'"),
    student_id: str | None = Query(None, description="Optional student user ID for personalized skill strengthening suggestions"),
):
    """Retrieve personalized technology and labour-market signals for selected domain."""
    return get_personalized_industry_alerts(domain_id=domain, student_id=student_id)


@router.get("/student/skill-explainability/{skill}")
async def skill_explainability(
    skill: str,
    student_id: str | None = Query(None, description="Optional student user ID for target career alignment"),
):
    """Return transparent 5-dimension evidence-based explainability breakdown for a skill."""
    return get_skill_explainability(skill_query=skill, student_id=student_id)


@router.get("/student/{student_id}/passport")
async def skill_passport(student_id: str):
    profiles = get_demo("student_profiles")
    skills_map = {s["id"]: s for s in get_demo("skills")}

    for p in profiles:
        if p["user_id"] == student_id:
            current = [
                {
                    **sk,
                    "skill_name": skills_map.get(sk["skill_id"], {}).get("name", ""),
                    "category": skills_map.get(sk["skill_id"], {}).get("category", ""),
                    "nsqf_level": skills_map.get(sk["skill_id"], {}).get("nsqf_level"),
                }
                for sk in p.get("skills", [])
            ]
            required = [
                {
                    "skill_id": sid,
                    "skill_name": skills_map.get(sid, {}).get("name", ""),
                    "category": skills_map.get(sid, {}).get("category", ""),
                    "nsqf_level": skills_map.get(sid, {}).get("nsqf_level"),
                }
                for sid in p.get("required_skills", [])
            ]
            missing = [
                r for r in required
                if r["skill_id"] not in {s["skill_id"] for s in p.get("skills", [])}
            ]
            return {
                "user_id": p["user_id"],
                "name": p["name"],
                "target_role": p["target_role"],
                "skill_match_pct": p["skill_match_pct"],
                "current_skills": current,
                "required_skills": required,
                "missing_skills": missing,
            }

    return {"error": "student not found"}


@router.get("/student/{student_id}/roadmap")
async def learning_roadmap(student_id: str):
    profiles = get_demo("student_profiles")
    skills_map = {s["id"]: s for s in get_demo("skills")}
    forecasts = get_demo("skill_forecasts")

    forecast_map = {}
    for f in forecasts:
        if f["skill_id"] not in forecast_map:
            forecast_map[f["skill_id"]] = f

    for p in profiles:
        if p["user_id"] == student_id:
            roadmap = []
            for idx, sid in enumerate(p.get("roadmap", []), start=1):
                skill = skills_map.get(sid, {})
                fc = forecast_map.get(sid, {})
                roadmap.append({
                    "step": idx,
                    "skill_id": sid,
                    "skill_name": skill.get("name", ""),
                    "category": skill.get("category", ""),
                    "nsqf_level": skill.get("nsqf_level"),
                    "future_demand": fc.get("future_demand", "high"),
                    "trend": fc.get("trend", "rising"),
                    "confidence": fc.get("confidence", 85),
                    "timeframe": fc.get("timeframe", "2025-2027"),
                    "key_drivers": fc.get("key_drivers", []),
                    "why": f"Recommended because {skill.get('name', 'this skill')} has "
                           f"{fc.get('future_demand', 'growing')} future demand with "
                           f"{fc.get('trend', 'rising')} trend and {fc.get('confidence', '85')}% confidence.",
                })
            return {
                "user_id": p["user_id"],
                "target_role": p["target_role"],
                "roadmap": roadmap,
            }

    return {"error": "student not found"}


@router.get("/students")
async def list_students():
    """List all demo students (for role selector)."""
    profiles = get_demo("student_profiles")
    return [
        {"user_id": p["user_id"], "name": p["name"], "target_role": p["target_role"],
         "skill_match_pct": p["skill_match_pct"]}
        for p in profiles
    ]


# ---------------------------------------------------------------------------
# Phase 12 Endpoints: Student Assessment & Quiz
# ---------------------------------------------------------------------------

@router.get("/student/assessment/quiz-questions")
async def get_quiz_questions():
    """Return standard diagnostic quiz questions and options for student assessment."""
    return {"questions": get_diagnostic_quiz_questions()}


@router.post("/student/assessment")
async def submit_student_assessment(submission: AssessmentSubmission):
    """Receive student data submission, validate, calculate grounded gap/quiz report, and persist."""
    # Convert Pydantic model to dictionary
    submission_data = {
        "name": submission.name,
        "education": submission.education,
        "career_goal": submission.career_goal,
        "district": submission.district or "Maharashtra",
        "current_skills": [
            {"skill_name": s.skill_name, "proficiency": s.proficiency}
            for s in submission.current_skills
        ],
        "interests": submission.interests,
        "quiz_answers": submission.quiz_answers,
    }

    # Evaluate against grounded SkillSetu labour-market data
    assessment_record = evaluate_student_assessment(submission_data)

    # Persist to database cache and Supabase write-through
    saved_record = save_student_assessment(assessment_record)

    return {
        "status": "success",
        "message": "Self-reported student assessment received and evaluated.",
        "assessment": saved_record,
    }


@router.get("/student/assessments")
async def list_student_assessments(
    source: str | None = Query(None, description="'USER_SUBMITTED' or 'DEMO_SYNTHETIC' or 'all'"),
    limit: int = Query(20, ge=1, le=100),
):
    """List all student assessments with clear separation of user-submitted vs demo data."""
    assessments = get_demo("student_assessments")
    filtered = assessments

    if source and source.lower() != "all":
        filtered = [a for a in filtered if a.get("source", "").lower() == source.lower()]

    return {
        "status": "success",
        "total": len(filtered),
        "assessments": filtered[:limit],
    }


@router.get("/student/assessment/{assessment_id}")
async def get_student_assessment(assessment_id: str):
    """Retrieve detailed assessment report by ID."""
    assessments = get_demo("student_assessments")
    for a in assessments:
        if a.get("id") == assessment_id:
            return {"status": "success", "assessment": a}

    raise HTTPException(status_code=404, detail="Student assessment record not found")


# ---------------------------------------------------------------------------
# Phase 16 Endpoints: AI-Powered Career Recommendation & Skill-Gap Engine
# ---------------------------------------------------------------------------

class ExplainAiQuery(BaseModel):
    prompt: str | None = None


@router.get("/student/recommendations/{student_id}")
@router.get("/student/{student_id}/recommendations")
async def get_student_recommendations(student_id: str):
    """Generate explainable career recommendations connecting student assessment, validated employer demand, and gov opportunities."""
    from app.services.career_recommendation_engine import compute_career_recommendations
    try:
        recommendations = compute_career_recommendations(student_id)
        return recommendations
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation engine error: {e}")


@router.post("/student/recommendations/{student_id}/explain-ai")
async def explain_student_recommendations_ai(student_id: str, query: ExplainAiQuery | None = None):
    """Generate conversational, encouraging AI Copilot explanation for the student's career recommendation."""
    from app.services.career_recommendation_engine import generate_ai_copilot_explanation
    try:
        custom_prompt = query.prompt if query else None
        res = await generate_ai_copilot_explanation(student_id, custom_prompt)
        return res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI explanation error: {e}")



