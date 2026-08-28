"""Demo/fallback LLM provider — rule-based responses when no API key is configured."""
from ai.provider import LLMProvider


# ponytail: keyword-matched canned responses formatted in rich Markdown
_RESPONSES = {
    "skill": (
        "### In-Demand Skills Intelligence\n\n"
        "Based on indexed SkillSetu labour-market data across Maharashtra:\n\n"
        "* **Top In-Demand Skills:** **Python** (appears in 26% of postings, 146 active roles), **PLC Programming** (14% demand), **Cloud Computing**, **Cybersecurity**, and **AI Agents**.\n"
        "* **Deficit Focus:** AI Agents and RAG show critical skill deficits with less than 20% institutional curriculum coverage.\n\n"
        "#### Recommended Action:\n"
        "Prioritize industry-partnered modules in Python, Industrial Automation, and Cloud Infrastructure at regional ITIs and polytechnics."
    ),
    "gap": (
        "### Identified Skill Deficit Analysis\n\n"
        "Comparison of employer job specifications against accredited vocational curricula:\n\n"
        "| Skill Name | Domain | Priority | Demand % | Coverage % | Deficit |\n"
        "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
        "| **Python** | Programming | **HIGH** | 26% | 18% | **8%** |\n"
        "| **PLC Programming** | Manufacturing | **HIGH** | 14% | 6% | **8%** |\n"
        "| **IoT** | Emerging Tech | **MEDIUM** | 10% | 3% | **7%** |\n"
        "| **Robotics** | Automation | **MEDIUM** | 9% | 2% | **7%** |\n\n"
        "> **Note:** Deficits represent unmet hiring demand across Maharashtra industrial clusters (Pune, Mumbai, Nagpur)."
    ),
    "pune": (
        "### Pune District Labour-Market Intelligence\n\n"
        "Analysis of Pune's industrial corridors (Pimpri-Chinchwad, Chakan, Hinjewadi, Talegaon):\n\n"
        "* **Active Job Openings:** **150** active postings tracked.\n"
        "* **Accredited Training Capacity:** **9** registered institutes offering **575** annual enrollment seats.\n"
        "* **Top In-Demand Roles:**\n"
        "  1. **Cloud Engineer** (11 postings)\n"
        "  2. **CAD Designer** (7 postings)\n"
        "  3. **Welder** (6 postings)\n"
        "  4. **Robotics Engineer** (6 postings)\n"
        "  5. **Healthcare Assistant** (6 postings)\n\n"
        "#### Recommended Policy Action:\n"
        "Expand intake capacity for CNC Machining and Mechatronics at Government ITI Pune and COEP Technological University to match local automotive automation expansion."
    ),
    "curriculum": (
        "### Curriculum Alignment Recommendations\n\n"
        "1. **Add AI Agents & RAG modules** to Computer Engineering & IT curricula (projected +24% hiring surge).\n"
        "2. **Introduce EV Battery Management Systems (BMS)** in automotive trade syllabi.\n"
        "3. **Audit Low-Placement Courses:** Flag courses with under 50% placement for vocational syllabus refresh."
    ),
    "career": (
        "### Recommended AI Engineer Career Roadmap\n\n"
        "1. **Stage 1 (Core):** Python (Advanced) + SQL & Database Design.\n"
        "2. **Stage 2 (Specialization):** Machine Learning Fundamentals + Deep Learning Architectures.\n"
        "3. **Stage 3 (Emerging Tech):** Generative AI, Retrieval-Augmented Generation (RAG), and Autonomous AI Agents.\n"
        "4. **Stage 4 (Industry Ready):** Cloud MLOps and Model Deployment Pipelines."
    ),
    "employer": (
        "### Employer Validation & Bottleneck Intelligence\n\n"
        "* **Validated Hiring Signals:** 15 active employer demand signals verified across Maharashtra.\n"
        "* **Primary Bottlenecks:** Experienced PLC Programmers, EV Powertrain Technicians, and AI System Engineers.\n"
        "* **Action:** Submit candidate skill feedback to accelerate state-level syllabus adjustments."
    ),
    "forecast": (
        "### 12-to-24 Month Skill Forecast\n\n"
        "* **Rising Exponentially:** AI Agents (+45%), Generative AI (+42%), EV Battery Tech (+38%).\n"
        "* **Stable Core:** Python, React, Cloud Computing, CNC Machining.\n"
        "* **Automating / Shifting:** Traditional Manual Drafting, Basic Data Entry."
    ),
}

_DEFAULT = (
    "### SkillSetu Labour-Market Intelligence\n\n"
    "SkillSetu continuously indexes 55+ skills, 560+ job postings, and 27 accredited training courses across 10 Maharashtra districts.\n\n"
    "**Suggested inquiries:**\n"
    "* *'What are the biggest skill gaps in Pune?'*\n"
    "* *'Which skills should I learn for an AI Engineer role?'*\n"
    "* *'What curriculum changes are recommended for polytechnics?'*\n"
    "* *'Which vocational courses show high placement rates?'*"
)


class DemoProvider(LLMProvider):
    """Rule-based fallback provider for demo mode."""

    async def generate(self, prompt: str, context: dict | None = None) -> str:
        prompt_lower = prompt.lower()
        for keyword, response in _RESPONSES.items():
            if keyword in prompt_lower:
                return response
        return _DEFAULT
