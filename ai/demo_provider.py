"""Demo/fallback LLM provider — rule-based responses when no API key is configured or offline."""
from ai.provider import LLMProvider


class DemoProvider(LLMProvider):
    """Rule-based fallback provider for demo mode and offline failover."""

    async def generate(self, prompt: str, context: dict | None = None) -> str:
        ctx = context or {}
        prompt_lower = prompt.lower()

        # 1. Handle unindexed / insufficient skill queries (e.g. Go/Golang, Rust, Ruby)
        if ctx.get("data_available_for_skill") is False or (
            ctx.get("queried_skill") and not ctx["queried_skill"].get("found_in_dataset")
        ):
            tech_name = ctx.get("queried_skill", {}).get("name", "the requested technology")
            return (
                f"### Data Availability Notice: {tech_name}\n\n"
                f"The current SkillSetu Maharashtra dataset does not contain sufficient **{tech_name}**-specific job records or accredited curriculum mappings to provide verified state-level demand metrics.\n\n"
                f"#### Verified Dataset Status:\n"
                f"* **State Job Postings Tracked:** **0** verified {tech_name} job postings in the current 10-district Maharashtra index.\n"
                f"* **Curriculum Coverage:** No state-accredited ITI, polytechnic, or MSBTE vocational course currently lists {tech_name} as a standalone core competency.\n"
                f"* **State Deficit Status:** Cannot compute a verified demand percentage or deficit gap for {tech_name} due to lack of local job telemetry.\n\n"
                f"#### General Industry Context:\n"
                f"**{tech_name}** is recognized in modern software engineering for high-concurrency microservices, cloud-native backend infrastructure, and systems tooling. Related programming and cloud competencies with active verified employer demand in Maharashtra include **Python** (26% demand, 146 active roles), **Java**, **React**, and **Cloud Computing (AWS/Kubernetes)**.\n\n"
                f"#### Recommendation:\n"
                f"To track {tech_name} demand systematically, submit candidate skill feedback via the Employer Dashboard or configure specialized tech job ingestion feeds."
            )

        # 2. Handle verified indexed skill queries (e.g. Python, PLC Programming, React)
        if ctx.get("data_available_for_skill") is True and ctx.get("queried_skill"):
            s = ctx["queried_skill"]
            dist_map = s.get("district_distribution", {})
            dist_str = ", ".join([f"**{d}** ({c} jobs)" for d, c in dist_map.items()]) if dist_map else "Statewide distribution across industrial clusters"
            
            sample_courses = s.get("sample_courses", [])
            if sample_courses:
                courses_str = "\n".join([f"* **{c['name']}** ({c.get('institute', 'State Technical Institute')})" for c in sample_courses])
            else:
                courses_str = "* Vocational curriculum modules currently integrated across state ITIs and polytechnics."

            return (
                f"### Verified Skill Intelligence: {s['name']}\n\n"
                f"Based on indexed SkillSetu labour-market records across Maharashtra:\n\n"
                f"* **Category / Domain:** {s.get('category', 'Technical')} (NSQF Level {s.get('nsqf_level', 'N/A')})\n"
                f"* **Active Hiring Demand:** Appears in **{s.get('demand_pct', 0)}%** of tracked job postings (**{s.get('demand_count', 0)}** active postings out of {s.get('total_jobs_tracked', 0)} total).\n"
                f"* **Curriculum Coverage:** Estimated at **{s.get('coverage_pct', 0)}%** across accredited state training programs.\n"
                f"* **Labour Deficit Gap:** **{s.get('gap_pct', 0)}%** ({s.get('priority', 'MEDIUM')} Priority Deficit).\n\n"
                f"#### Regional Distribution:\n"
                f"{dist_str}\n\n"
                f"#### Accredited Training Modules:\n"
                f"{courses_str}\n\n"
                f"#### Recommended Action:\n"
                f"Expand industry-aligned practical training in **{s['name']}** at regional technical institutions to bridge the {s.get('gap_pct', 0)}% curriculum deficit."
            )

        # 3. District-specific queries (when no specific unindexed skill is queried)
        if ctx.get("focused_district"):
            fd = ctx["focused_district"]
            dname = fd.get("district", "Maharashtra District")
            roles_list = [r.get("role", str(r)) if isinstance(r, dict) else str(r) for r in fd.get("top_roles", [])[:5]]
            skills_list = [s.get("skill_name", str(s)) if isinstance(s, dict) else str(s) for s in fd.get("top_skills", [])[:5]]
            roles_str = ", ".join(roles_list) if roles_list else "Technical and vocational trades"
            skills_str = ", ".join(skills_list) if skills_list else "Engineering and automation skills"
            return (
                f"### {dname} District Labour-Market Intelligence\n\n"
                f"Analysis of industrial corridors in {dname}:\n\n"
                f"* **Active Job Openings:** **{fd.get('total_jobs', 0)}** active postings tracked.\n"
                f"* **Accredited Training Capacity:** **{fd.get('total_courses', 0)}** registered courses offering **{fd.get('total_enrolment', 0)}** annual enrollment seats.\n"
                f"* **Top In-Demand Roles:** {roles_str}.\n"
                f"* **Top In-Demand Skills:** {skills_str}.\n\n"
                f"#### Recommended Policy Action:\n"
                f"Align local ITI and polytechnic batch sizes in {dname} with local industrial cluster expansion."
            )

        # 4. Gaps / Deficit query
        if "gap" in prompt_lower or "deficit" in prompt_lower:
            return (
                "### Identified Skill Deficit Analysis\n\n"
                "Comparison of employer job specifications against accredited vocational curricula in Maharashtra:\n\n"
                "| Skill Name | Domain | Priority | Demand % | Coverage % | Deficit |\n"
                "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
                "| **Python** | Programming | **HIGH** | 26% | 18% | **8%** |\n"
                "| **PLC Programming** | Manufacturing | **HIGH** | 14% | 6% | **8%** |\n"
                "| **IoT** | Emerging Tech | **MEDIUM** | 10% | 3% | **7%** |\n"
                "| **Robotics** | Automation | **MEDIUM** | 9% | 2% | **7%** |\n\n"
                "> **Note:** Deficits represent unmet hiring demand across Maharashtra industrial clusters (Pune, Mumbai, Nagpur)."
            )

        # 5. Curriculum query
        if "curriculum" in prompt_lower or "syllabus" in prompt_lower:
            return (
                "### Curriculum Alignment Recommendations\n\n"
                "1. **Add AI Agents & RAG modules** to Computer Engineering & IT curricula (projected +24% hiring surge).\n"
                "2. **Introduce EV Battery Management Systems (BMS)** in automotive trade syllabi.\n"
                "3. **Audit Low-Placement Courses:** Flag courses with under 50% placement for vocational syllabus refresh."
            )

        # 6. Career roadmap query
        if "career" in prompt_lower or "roadmap" in prompt_lower:
            return (
                "### Recommended Technical Career Roadmap\n\n"
                "1. **Stage 1 (Core Foundations):** Core Programming / Engineering Principles + Applied Mathematics.\n"
                "2. **Stage 2 (Specialization):** Domain Frameworks, Hands-on Tooling, and Practical Projects.\n"
                "3. **Stage 3 (Advanced Systems):** Cloud Infrastructure, Distributed Architectures, and Automated Testing.\n"
                "4. **Stage 4 (Industry Placement):** Production Internship / NAPS Apprenticeship Capstone."
            )

        # 7. Employer feedback query
        if "employer" in prompt_lower or "validation" in prompt_lower:
            return (
                "### Employer Validation & Bottleneck Intelligence\n\n"
                "* **Validated Hiring Signals:** 15 active employer demand signals verified across Maharashtra.\n"
                "* **Primary Bottlenecks:** Experienced PLC Programmers, EV Powertrain Technicians, and AI System Engineers.\n"
                "* **Action:** Submit candidate skill feedback to accelerate state-level syllabus adjustments."
            )

        # 8. Forecast query
        if "forecast" in prompt_lower or "trend" in prompt_lower:
            return (
                "### 12-to-24 Month Skill Forecast\n\n"
                "* **Rising Exponentially:** AI Agents (+45%), Generative AI (+42%), EV Battery Tech (+38%).\n"
                "* **Stable Core:** Python, React, Cloud Computing, CNC Machining.\n"
                "* **Automating / Shifting:** Traditional Manual Drafting, Basic Data Entry."
            )

        # Default Maharashtra overview
        return (
            "### SkillSetu Labour-Market Intelligence\n\n"
            "SkillSetu continuously indexes 55+ skills, 560+ job postings, and 27 accredited training courses across 10 Maharashtra districts.\n\n"
            "**Suggested inquiries:**\n"
            "* *'Tell me about requirement for Python developer'*\n"
            "* *'What are the biggest skill gaps in Pune?'*\n"
            "* *'What is the demand for Go developer?'*\n"
            "* *'Which vocational courses show high placement rates?'*"
        )
