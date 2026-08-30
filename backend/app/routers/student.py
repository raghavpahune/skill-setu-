"""Student API — Skill Passport, learning roadmap, personalized industry alerts, skill explainability, and student self-assessment."""
from fastapi import APIRouter, Query, HTTPException, Depends, status
from pydantic import BaseModel, Field
from app.core.security import get_current_user, get_optional_current_user
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


@router.get("/student/me/passport")
async def my_skill_passport(
    current_user: dict = Depends(get_current_user),
):
    """Retrieve the authenticated student's personalized Skill Passport from their real assessment."""
    user_id = current_user.get("id")
    user_email = current_user.get("email")
    skills_map = {s["id"]: s for s in get_demo("skills")}
    skills_name_map = {s["name"].lower(): s for s in get_demo("skills")}

    # 1. Check for real student assessment submission
    assessments = get_demo("student_assessments")
    matched_assessment = next(
        (a for a in assessments if a.get("user_id") == user_id or a.get("id") == user_id or (user_email and a.get("user_email") == user_email)),
        None
    )

    if matched_assessment:
        target_role = matched_assessment.get("career_goal", "AI Engineer")
        from app.services.student_service import ROLE_REQUIREMENTS_MAP
        req_sids = ROLE_REQUIREMENTS_MAP.get(target_role.lower(), ["sk-001", "sk-002", "sk-003", "sk-004", "sk-005", "sk-006"])

        curr_skills = []
        curr_sids = set()
        for cs in matched_assessment.get("current_skills", []):
            s_name = cs.get("skill_name", "")
            sid = cs.get("skill_id")
            if not sid and s_name.lower() in skills_name_map:
                sid = skills_name_map[s_name.lower()]["id"]
            if sid:
                curr_sids.add(sid)
            sk_obj = skills_map.get(sid, {})
            curr_skills.append({
                "skill_id": sid or f"sk-custom-{len(curr_skills)+1}",
                "skill_name": s_name or sk_obj.get("name", "Custom Skill"),
                "proficiency": cs.get("proficiency", "intermediate"),
                "category": cs.get("category") or sk_obj.get("category", "General"),
                "nsqf_level": cs.get("nsqf_level") or sk_obj.get("nsqf_level", 5),
            })

        required = [
            {
                "skill_id": sid,
                "skill_name": skills_map.get(sid, {}).get("name", sid),
                "category": skills_map.get(sid, {}).get("category", "General"),
                "nsqf_level": skills_map.get(sid, {}).get("nsqf_level", 5),
            }
            for sid in req_sids
        ]
        missing = [r for r in required if r["skill_id"] not in curr_sids]

        return {
            "user_id": user_id,
            "name": matched_assessment.get("name") or current_user.get("full_name", "Student Candidate"),
            "target_role": target_role,
            "skill_match_pct": matched_assessment.get("skill_match_pct", 65),
            "current_skills": curr_skills,
            "required_skills": required,
            "missing_skills": missing,
            "source": "USER_SUBMITTED",
            "is_personalized": True,
        }

    # 2. Check for student profile
    profiles = get_demo("student_profiles")
    matched_profile = next((p for p in profiles if p.get("user_id") == user_id or p.get("id") == user_id), None)

    if matched_profile:
        current = [
            {
                **sk,
                "skill_name": skills_map.get(sk["skill_id"], {}).get("name", ""),
                "category": skills_map.get(sk["skill_id"], {}).get("category", ""),
                "nsqf_level": skills_map.get(sk["skill_id"], {}).get("nsqf_level"),
            }
            for sk in matched_profile.get("skills", [])
        ]
        required = [
            {
                "skill_id": sid,
                "skill_name": skills_map.get(sid, {}).get("name", ""),
                "category": skills_map.get(sid, {}).get("category", ""),
                "nsqf_level": skills_map.get(sid, {}).get("nsqf_level"),
            }
            for sid in matched_profile.get("required_skills", [])
        ]
        missing = [
            r for r in required
            if r["skill_id"] not in {s["skill_id"] for s in matched_profile.get("skills", [])}
        ]
        return {
            "user_id": user_id,
            "name": current_user.get("full_name") or matched_profile["name"],
            "target_role": matched_profile["target_role"],
            "skill_match_pct": matched_profile["skill_match_pct"],
            "current_skills": current,
            "required_skills": required,
            "missing_skills": missing,
            "source": matched_profile.get("source", "DEMO_SYNTHETIC"),
            "is_personalized": False,
        }

    # 3. Explicit unassessed state for new accounts (no silent fallback to demo student)
    return {
        "user_id": user_id,
        "name": current_user.get("full_name", "Student Candidate"),
        "has_assessment": False,
        "is_personalized": False,
        "source": "NO_SUBMISSION",
        "message": "No personal assessment completed yet. Take the 3-minute diagnostic to generate your personalized Skill Passport.",
        "target_role": None,
        "skill_match_pct": 0,
        "current_skills": [],
        "required_skills": [],
        "missing_skills": [],
    }


@router.get("/student/{student_id}/passport")
async def skill_passport(
    student_id: str,
    current_user: dict | None = Depends(get_optional_current_user),
):
    if student_id == "me" and current_user:
        return await my_skill_passport(current_user=current_user)

    profiles = get_demo("student_profiles")
    skills_map = {s["id"]: s for s in get_demo("skills")}
    skills_name_map = {s["name"].lower(): s for s in get_demo("skills")}

    # First check student_assessments cache for user-submitted profiles
    assessments = get_demo("student_assessments")
    for a in assessments:
        if a.get("id") == student_id or a.get("user_id") == student_id:
            target_role = a.get("career_goal", "AI Engineer")
            from app.services.student_service import ROLE_REQUIREMENTS_MAP
            req_sids = ROLE_REQUIREMENTS_MAP.get(target_role.lower(), ["sk-001", "sk-002", "sk-003", "sk-004", "sk-005", "sk-006"])

            curr_skills = []
            curr_sids = set()
            for cs in a.get("current_skills", []):
                s_name = cs.get("skill_name", "")
                sid = cs.get("skill_id")
                if not sid and s_name.lower() in skills_name_map:
                    sid = skills_name_map[s_name.lower()]["id"]
                if sid:
                    curr_sids.add(sid)
                sk_obj = skills_map.get(sid, {})
                curr_skills.append({
                    "skill_id": sid or f"sk-custom-{len(curr_skills)+1}",
                    "skill_name": s_name or sk_obj.get("name", "Custom Skill"),
                    "proficiency": cs.get("proficiency", "intermediate"),
                    "category": cs.get("category") or sk_obj.get("category", "General"),
                    "nsqf_level": cs.get("nsqf_level") or sk_obj.get("nsqf_level", 5),
                })

            required = [
                {
                    "skill_id": sid,
                    "skill_name": skills_map.get(sid, {}).get("name", sid),
                    "category": skills_map.get(sid, {}).get("category", "General"),
                    "nsqf_level": skills_map.get(sid, {}).get("nsqf_level", 5),
                }
                for sid in req_sids
            ]
            missing = [r for r in required if r["skill_id"] not in curr_sids]

            return {
                "user_id": a.get("id"),
                "name": a.get("name", "Student Candidate"),
                "target_role": target_role,
                "skill_match_pct": a.get("skill_match_pct", 50),
                "current_skills": curr_skills,
                "required_skills": required,
                "missing_skills": missing,
                "source": a.get("source", "USER_SUBMITTED"),
                "is_personalized": True,
            }

    for p in profiles:
        if p.get("user_id") == student_id or p.get("id") == student_id:
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
                "user_id": p.get("user_id") or p.get("id"),
                "name": p["name"],
                "target_role": p["target_role"],
                "skill_match_pct": p["skill_match_pct"],
                "current_skills": current,
                "required_skills": required,
                "missing_skills": missing,
                "source": p.get("source", "DEMO_SYNTHETIC"),
                "is_personalized": False,
            }

    return {"error": "student not found"}



@router.get("/student/me/roadmap")
async def my_learning_roadmap(
    current_user: dict = Depends(get_current_user),
):
    """Retrieve the authenticated student's personalized learning roadmap."""
    return await learning_roadmap(student_id=current_user.get("id"), current_user=current_user)


@router.get("/student/{student_id}/roadmap")
async def learning_roadmap(
    student_id: str,
    current_user: dict | None = Depends(get_optional_current_user),
):
    if student_id == "me" and current_user:
        student_id = current_user.get("id")
    profiles = get_demo("student_profiles")
    skills_map = {s["id"]: s for s in get_demo("skills")}
    forecasts = get_demo("skill_forecasts")

    forecast_map = {}
    for f in forecasts:
        if f["skill_id"] not in forecast_map:
            forecast_map[f["skill_id"]] = f

    # First check student_assessments for real user submissions
    assessments = get_demo("student_assessments")
    for a in assessments:
        if a.get("id") == student_id or a.get("user_id") == student_id or (current_user and a.get("user_id") == current_user.get("id")):
            target_role = a.get("career_goal", "AI Engineer")
            from app.services.student_service import ROLE_REQUIREMENTS_MAP
            req_sids = ROLE_REQUIREMENTS_MAP.get(target_role.lower(), ["sk-003", "sk-004", "sk-006", "sk-005"])
            curr_sids = {cs.get("skill_id") for cs in a.get("current_skills", []) if cs.get("skill_id")}
            roadmap_sids = [sid for sid in req_sids if sid not in curr_sids] or req_sids[:3]

            roadmap = []
            for idx, sid in enumerate(roadmap_sids, start=1):
                skill = skills_map.get(sid, {"id": sid, "name": "Priority Competency", "category": "General", "nsqf_level": 5})
                fc = forecast_map.get(sid, {})
                roadmap.append({
                    "step": idx,
                    "skill_id": sid,
                    "skill_name": skill.get("name", sid),
                    "category": skill.get("category", "General"),
                    "nsqf_level": skill.get("nsqf_level", 5),
                    "future_demand": fc.get("future_demand", "high"),
                    "trend": fc.get("trend", "rising"),
                    "confidence": fc.get("confidence", 85),
                    "timeframe": fc.get("timeframe", "2025-2027"),
                    "key_drivers": fc.get("key_drivers", ["Labour market expansion", "Employer demand"]),
                    "why": f"Recommended because {skill.get('name', 'this skill')} bridges critical gap for {target_role}.",
                })
            return {
                "user_id": a.get("id"),
                "target_role": target_role,
                "roadmap": roadmap,
            }

    # Then check demo profiles
    for p in profiles:
        if p.get("user_id") == student_id or p.get("id") == student_id:
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
                "user_id": p.get("user_id") or p.get("id"),
                "target_role": p["target_role"],
                "roadmap": roadmap,
            }

    return {
        "user_id": student_id,
        "target_role": None,
        "has_roadmap": False,
        "roadmap": [],
        "message": "No personal assessment completed yet. Complete your diagnostic to view your learning roadmap.",
    }



@router.get("/students")
async def list_students():
    """List all demo students + user submitted assessments (for role selector)."""
    profiles = get_demo("student_profiles")
    results = [
        {"user_id": p.get("user_id") or p.get("id"), "name": p["name"], "target_role": p["target_role"],
         "skill_match_pct": p["skill_match_pct"], "source": p.get("source", "DEMO_SYNTHETIC")}
        for p in profiles
    ]
    assessments = get_demo("student_assessments")
    for a in assessments:
        if a.get("source") == "USER_SUBMITTED" or a.get("id", "").startswith("ast-usr-"):
            aid = a.get("id")
            if not any(r["user_id"] == aid for r in results):
                results.append({
                    "user_id": aid,
                    "name": f"{a.get('name', 'Candidate')} (Self-Assessed)",
                    "target_role": a.get("career_goal", "Target Career"),
                    "skill_match_pct": a.get("skill_match_pct", 50),
                    "source": "USER_SUBMITTED",
                })
    return results


# ---------------------------------------------------------------------------
# Phase 12 Endpoints: Student Assessment & Quiz
# ---------------------------------------------------------------------------

@router.get("/student/assessment/quiz-questions")
async def get_quiz_questions():
    """Return standard diagnostic quiz questions and options for student assessment."""
    return {"questions": get_diagnostic_quiz_questions()}


from app.core.security import get_optional_current_user, get_current_user


@router.post("/student/assessment")
async def submit_student_assessment(
    submission: AssessmentSubmission,
    current_user: dict | None = Depends(get_optional_current_user),
):
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

    # Attach authenticated user identity if logged in
    if current_user:
        assessment_record["user_id"] = current_user.get("id")
        assessment_record["user_email"] = current_user.get("email")

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
    current_user: dict | None = Depends(get_optional_current_user),
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
async def get_student_assessment(
    assessment_id: str,
    current_user: dict | None = Depends(get_optional_current_user),
):
    """Retrieve detailed assessment report by ID with ownership verification."""
    assessments = get_demo("student_assessments")
    for a in assessments:
        if a.get("id") == assessment_id:
            # If the record is private to a specific user, ensure only owner or admin can view
            record_user_id = a.get("user_id")
            if record_user_id and current_user:
                user_role = (current_user.get("role") or "").upper()
                if user_role != "ADMIN" and current_user.get("id") != record_user_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Forbidden: You do not have permission to view another student's assessment report",
                    )
            return {"status": "success", "assessment": a}

    raise HTTPException(status_code=404, detail="Student assessment record not found")


# ---------------------------------------------------------------------------
# Phase 16 Endpoints: AI-Powered Career Recommendation & Skill-Gap Engine
# ---------------------------------------------------------------------------

class ExplainAiQuery(BaseModel):
    prompt: str | None = None


@router.get("/student/recommendations/{student_id}")
@router.get("/student/{student_id}/recommendations")
async def get_student_recommendations(
    student_id: str,
    current_user: dict | None = Depends(get_optional_current_user),
):
    """Generate explainable career recommendations connecting student assessment, validated employer demand, and gov opportunities."""
    from app.services.career_recommendation_engine import compute_career_recommendations
    resolved_id = student_id
    if student_id == "me" and current_user:
        resolved_id = current_user.get("id") or "me"
    try:
        recommendations = compute_career_recommendations(resolved_id)
        return recommendations
    except ValueError as e:
        if student_id == "me" or (current_user and resolved_id == current_user.get("id")):
            return {
                "status": "unassessed",
                "has_assessment": False,
                "message": "Complete your diagnostic assessment to receive personalized career recommendations.",
                "recommended_careers": [],
            }
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation engine error: {e}")


@router.post("/student/recommendations/{student_id}/explain-ai")
async def explain_student_recommendations_ai(
    student_id: str,
    query: ExplainAiQuery | None = None,
    current_user: dict | None = Depends(get_optional_current_user),
):
    """Generate conversational, encouraging AI Copilot explanation for the student's career recommendation."""
    from app.services.career_recommendation_engine import generate_ai_copilot_explanation
    resolved_id = student_id
    if student_id == "me" and current_user:
        resolved_id = current_user.get("id") or "me"
    try:
        custom_prompt = query.prompt if query else None
        res = await generate_ai_copilot_explanation(resolved_id, custom_prompt)
        return res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI explanation error: {e}")




