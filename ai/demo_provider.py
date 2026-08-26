"""Demo/fallback LLM provider — rule-based responses when no API key is configured."""
from ai.provider import LLMProvider


# ponytail: keyword-matched canned responses — good enough for demo, no API needed
_RESPONSES = {
    "skill": (
        "[Demo Mode] Based on SkillSetu data, the top in-demand skills in Maharashtra are: "
        "Python (appearing in 45% of job postings), Machine Learning (38%), Cloud Computing (32%), "
        "Cybersecurity (28%), and AI Agents (25%). These skills show strong employer validation "
        "and rising future demand trends. Consider prioritizing AI Agents and RAG — both show "
        "critical skill gaps with less than 30% curriculum coverage."
    ),
    "gap": (
        "[Demo Mode] Key skill gaps identified: AI Agents (gap: 58%, priority: CRITICAL), "
        "RAG (gap: 52%, priority: CRITICAL), LLM Engineering (gap: 48%, priority: HIGH), "
        "EV Battery Technology (gap: 45%, priority: HIGH). These gaps represent the difference "
        "between employer demand and current training program coverage across Maharashtra."
    ),
    "pune": (
        "[Demo Mode] Pune's labour market analysis shows: Top roles — AI Engineer, Full Stack Developer, "
        "Automation Engineer. The district has strong IT/ITES demand (60% of postings) with growing "
        "EV and manufacturing sectors. Key recommendation: Expand AI/ML and EV technology training "
        "capacity at existing ITIs and polytechnics."
    ),
    "curriculum": (
        "[Demo Mode] Curriculum recommendations: 1) Add AI Agents module to ML courses (gap: 58%). "
        "2) Introduce RAG pipeline training (gap: 52%). 3) Update EV Battery Technology content "
        "in automotive courses. 4) Review 'Traditional Office Data Entry' course — high enrolment "
        "but only 20% placement rate, flagged as possible oversupply."
    ),
    "career": (
        "[Demo Mode] For an AI Engineer career path, your recommended learning roadmap: "
        "1) Strengthen Deep Learning foundations, 2) Learn Generative AI concepts, "
        "3) Master RAG pipeline architecture, 4) Build AI Agent systems. "
        "Current industry demand is rising with 82% confidence for 12-month forecast."
    ),
    "employer": (
        "[Demo Mode] Employer validation summary: 15 skill demands confirmed by employers, "
        "3 corrections submitted (mostly requesting higher proficiency levels), "
        "1 rejection (Prompt Engineering as standalone hiring skill). "
        "Top difficult-to-hire skills: AI Agents, RAG, EV Battery Technology."
    ),
    "forecast": (
        "[Demo Mode] Rising skills (next 12 months): AI Agents (confidence: 82%), "
        "Generative AI (85%), RAG (80%), EV Battery Technology (80%), "
        "Cybersecurity (83%), Industry 4.0 (74%). Stable: Python, React, Cloud Computing. "
        "Declining: Traditional Welding, Plumbing (being automated)."
    ),
}

_DEFAULT = (
    "[Demo Mode] AI service running without API key — showing rule-based recommendation. "
    "SkillSetu tracks 55+ skills across IT, manufacturing, healthcare, EV, and agriculture sectors "
    "in Maharashtra. Ask about specific skills, gaps, districts, careers, or forecasts for "
    "detailed data-driven insights."
)


class DemoProvider(LLMProvider):
    """Rule-based fallback provider for demo mode."""

    async def generate(self, prompt: str, context: dict | None = None) -> str:
        prompt_lower = prompt.lower()
        for keyword, response in _RESPONSES.items():
            if keyword in prompt_lower:
                return response
        return _DEFAULT
