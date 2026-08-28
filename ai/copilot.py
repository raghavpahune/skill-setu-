"""AI Copilot orchestrator — selects provider, fetches query-specific context, returns grounded answer."""
import os
import sys
import re
import logging
from collections import Counter
from pathlib import Path

logger = logging.getLogger("skillsetu.ai.copilot")

# Ensure backend app is importable
_backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from ai.provider import LLMProvider
from ai.gemini_provider import GeminiProvider
from ai.demo_provider import DemoProvider

KNOWN_EXTERNAL_TECHS = {
    "go": "Go / Golang",
    "golang": "Go / Golang",
    "go lang": "Go / Golang",
    "rust": "Rust",
    "ruby": "Ruby",
    "ruby on rails": "Ruby on Rails",
    "rails": "Ruby on Rails",
    "c++": "C++",
    "cpp": "C++",
    "c#": "C#",
    "csharp": "C#",
    "swift": "Swift",
    "kotlin": "Kotlin",
    "php": "PHP",
    "scala": "Scala",
    "typescript": "TypeScript",
    "angular": "Angular",
    "angularjs": "Angular",
    "vue": "Vue.js",
    "vuejs": "Vue.js",
    "solidity": "Solidity",
    "elixir": "Elixir",
    "haskell": "Haskell",
    "perl": "Perl",
    "dart": "Dart",
    "zig": "Zig",
}


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


def extract_queried_skill(question: str, skills_list: list[dict]) -> dict | None:
    """Detect if the user is asking about a specific technical skill or programming language."""
    if not question:
        return None
    q_lower = question.lower()

    # 1. Match against indexed skills (and synonyms) using word boundaries
    for s in skills_list:
        name = s.get("name", "")
        if not name:
            continue
        pattern = r"\b" + re.escape(name.lower()) + r"\b"
        if re.search(pattern, q_lower):
            return {"type": "indexed", "skill": s, "name": name}
        for syn in s.get("synonyms", []):
            if not syn:
                continue
            syn_pat = r"\b" + re.escape(syn.lower()) + r"\b"
            if re.search(syn_pat, q_lower):
                return {"type": "indexed", "skill": s, "name": name}

    # 2. Check specific Go/Golang patterns
    if (
        re.search(r"\b(golang|go\s*lang)\b", q_lower)
        or re.search(r"\bgo\s+(developer|engineer|programmer|language|jobs?|demand|requirement|role|stack|tech)\b", q_lower)
        or re.search(r"\b(?:requirement|demand|jobs?|role)\s+(?:of|for|in)?\s+go\b", q_lower)
        or re.search(r"\b(developer|engineer|programmer)\s+(?:in|for|of)?\s*go\b", q_lower)
    ):
        return {"type": "unindexed", "name": "Go / Golang"}

    # 3. Match against known unindexed languages/frameworks
    for term, label in KNOWN_EXTERNAL_TECHS.items():
        if term in ("go", "golang", "go lang"):
            continue
        pattern = r"\b" + re.escape(term) + r"\b"
        if re.search(pattern, q_lower):
            return {"type": "unindexed", "name": label}

    # 4. Generic skill/developer query extraction pattern
    m = re.search(r"\b(?:requirement|demand|jobs?|skills?|career)\s+(?:of|for|in)?\s+(?:a\s+|an\s+)?([a-zA-Z0-9#\+\.\-]+)\s+(?:developer|engineer|programmer|specialist|language|role)\b", q_lower)
    if m:
        word = m.group(1).strip()
        if word not in ("a", "an", "the", "good", "any", "lead", "senior", "junior"):
            return {"type": "unindexed", "name": word.capitalize()}

    m2 = re.search(r"\b([a-zA-Z0-9#\+\.\-]+)\s+(?:developer|engineer|programmer|language)\b", q_lower)
    if m2:
        word = m2.group(1).strip()
        if word not in ("a", "an", "the", "good", "software", "web", "cloud", "frontend", "backend", "fullstack", "mobile"):
            return {"type": "unindexed", "name": word.capitalize()}

    return None


def _build_context(role: str, question: str = "") -> dict:
    """Fetch relevant structured data to ground the response accurately without polluting query context."""
    try:
        from app.db import get_demo
        from app.services.gap_engine import compute_gaps

        skills = get_demo("skills")
        jobs = get_demo("jobs")
        job_skills = get_demo("job_skills")
        courses = get_demo("courses")
        course_skills = get_demo("course_skills")

        # Check for district mentions
        q_lower = question.lower() if question else ""
        focused_district = None
        if question:
            from app.services.district_service import get_all_districts, get_district_plan
            for d in get_all_districts():
                dname = d.get("name", "")
                if dname and dname.lower() in q_lower:
                    plan = get_district_plan(dname)
                    focused_district = {
                        "district": dname,
                        "total_jobs": plan.get("total_jobs"),
                        "total_courses": plan.get("total_courses"),
                        "total_enrolment": plan.get("total_enrolment"),
                        "top_roles": plan.get("top_roles", [])[:5],
                        "top_skills": plan.get("top_skills", [])[:5],
                        "industry_demand": plan.get("industry_demand", [])[:4],
                    }
                    break

        # Check if query targets a specific skill
        queried_skill_info = extract_queried_skill(question, skills)

        if queried_skill_info:
            if queried_skill_info["type"] == "indexed":
                skill_obj = queried_skill_info["skill"]
                sid = skill_obj["id"]
                sname = skill_obj["name"]

                # Filter matching jobs for this specific skill
                matching_js = [js for js in job_skills if js["skill_id"] == sid]
                matching_job_ids = {js["job_id"] for js in matching_js}
                matching_jobs = [j for j in jobs if j["id"] in matching_job_ids]

                total_jobs_count = len(jobs)
                demand_count = len(matching_jobs)
                demand_pct = round((demand_count / total_jobs_count) * 100) if total_jobs_count else 0

                # District distribution for this skill
                district_counts = dict(Counter(j.get("district", "Unknown") for j in matching_jobs).most_common(5))

                # Gap engine metrics for this skill
                all_gaps = compute_gaps(focused_district.get("district") if focused_district else None)
                gap_entry = next((g for g in all_gaps if g["skill_id"] == sid), None)

                # Teaching courses for this skill
                teaching_course_ids = {cs["course_id"] for cs in course_skills if cs["skill_id"] == sid}
                teaching_courses = [
                    {"id": c["id"], "name": c.get("name", ""), "institute": c.get("institute", "")}
                    for c in courses if c["id"] in teaching_course_ids
                ][:5]

                context = {
                    "query_type": "skill_specific",
                    "data_available_for_skill": True,
                    "queried_skill": {
                        "id": sid,
                        "name": sname,
                        "category": skill_obj.get("category", "General"),
                        "nsqf_level": skill_obj.get("nsqf_level"),
                        "found_in_dataset": True,
                        "demand_count": demand_count,
                        "total_jobs_tracked": total_jobs_count,
                        "demand_pct": demand_pct,
                        "coverage_pct": gap_entry["coverage_pct"] if gap_entry else 0,
                        "gap_pct": gap_entry["gap_pct"] if gap_entry else 0,
                        "priority": gap_entry["priority"] if gap_entry else "LOW",
                        "district_distribution": district_counts,
                        "sample_courses": teaching_courses,
                    },
                }
                if focused_district:
                    context["focused_district"] = focused_district
                return context

            else:
                # Skill is unindexed / unsupported in current dataset (e.g. Go/Golang, Rust, etc.)
                tech_name = queried_skill_info["name"]
                context = {
                    "query_type": "skill_specific",
                    "data_available_for_skill": False,
                    "queried_skill": {
                        "name": tech_name,
                        "found_in_dataset": False,
                        "verified_job_count": 0,
                        "verified_course_count": 0,
                        "message": f"No verified job postings or accredited state courses for '{tech_name}' exist in the current Maharashtra 10-district dataset.",
                    },
                }
                if focused_district:
                    context["focused_district"] = focused_district
                return context

        # General / District / Role Context when no specific skill is queried
        context = {
            "query_type": "general_overview",
            "top_skill_gaps": compute_gaps()[:10],
            "total_skills_tracked": len(skills),
            "total_jobs": len(jobs),
        }

        if role == "student":
            context["student_profiles"] = [
                {"name": p["name"], "target_role": p["target_role"], "match": p["skill_match_pct"]}
                for p in get_demo("student_profiles")
            ]
        elif role == "government":
            from app.services.district_service import get_all_districts
            context["districts"] = get_all_districts()
        elif role == "institute":
            context["institutes_summary"] = {
                "total_courses": len(courses),
                "sample_institutes": sorted(list(set(c.get("institute", "") for c in courses if c.get("institute"))))[:6],
            }
        elif role == "employer":
            feedback = get_demo("employer_feedback")
            context["pending_validations"] = len([f for f in feedback if f["status"] == "pending"])
            context["confirmed"] = len([f for f in feedback if f["status"] == "confirmed"])

        if focused_district:
            context["focused_district"] = focused_district

        if question:
            for p in get_demo("student_profiles"):
                target = p.get("target_role", "")
                if target and target.lower() in q_lower:
                    skills_map = {s["id"]: s.get("name", "") for s in skills}
                    context["focused_career_role"] = {
                        "role": target,
                        "required_skills": [skills_map.get(sid, sid) for sid in p.get("required_skills", [])],
                        "roadmap": [skills_map.get(sid, sid) for sid in p.get("roadmap", [])],
                    }
                    break

        return context
    except Exception as e:
        logger.warning(f"[Copilot] Failed to build context: {e}")
        return {}


async def handle_question(question: str, role: str = "student") -> dict:
    """Handle a copilot question end-to-end with live inference and resilient offline fallback."""
    provider = _get_provider()
    context = _build_context(role, question)
    is_live_ai = isinstance(provider, GeminiProvider)

    logger.info(f"[Copilot] Query: '{question}' (provider={provider.__class__.__name__}, is_live={is_live_ai}, role={role})")

    if is_live_ai:
        try:
            answer = await provider.generate(question, context)
            return {
                "answer": answer,
                "role": role,
                "demo_mode": False,
                "data_grounded": bool(context),
                "model": getattr(provider, "model", "gemini-3.6-flash"),
            }
        except Exception as e:
            err_msg = str(e)
            logger.error(f"[Copilot] Live generation error, switching to rule-based offline fallback: {err_msg}")
            # Fallback to DemoProvider rule-based intelligence so application never crashes
            try:
                demo_prov = DemoProvider()
                fallback_answer = await demo_prov.generate(question, context)
                return {
                    "answer": fallback_answer,
                    "role": role,
                    "demo_mode": True,
                    "data_grounded": bool(context),
                    "model": "Rule-Based Offline Intelligence",
                    "notice": "AI service temporarily unavailable. Switched to offline intelligence.",
                }
            except Exception:
                return {
                    "answer": f"[Gemini API Error] {err_msg}\n\nPlease check your Google AI Studio quota / API key permissions on Render.",
                    "role": role,
                    "demo_mode": True,
                    "data_grounded": bool(context),
                    "error_details": err_msg,
                    "model": "Rule-Based Offline Intelligence",
                }

    # Demo mode provider
    answer = await provider.generate(question, context)
    return {
        "answer": answer,
        "role": role,
        "demo_mode": True,
        "data_grounded": bool(context),
        "model": "Rule-Based Offline Intelligence",
    }
