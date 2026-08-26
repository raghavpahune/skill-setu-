"""Gemini LLM provider implementation."""
import os
from ai.provider import LLMProvider


class GeminiProvider(LLMProvider):
    """Google Gemini API provider."""

    def __init__(self):
        try:
            from google import genai
            api_key = os.getenv("GEMINI_API_KEY", "")
            self.client = genai.Client(api_key=api_key) if api_key else None
            self.model = "gemini-2.0-flash"
        except ImportError:
            self.client = None

    async def generate(self, prompt: str, context: dict | None = None) -> str:
        if not self.client:
            raise RuntimeError("Gemini client not initialized — missing API key or google-genai package")

        system_instruction = (
            "You are SkillSetu AI Copilot, a labour-market intelligence assistant for Maharashtra, India. "
            "You answer questions about skill demand, skill gaps, curriculum recommendations, "
            "future skill forecasts, industry signals, and career guidance. "
            "Always ground your answers in the provided data context. "
            "Cite specific numbers and evidence. Be concise and actionable. "
            "If the data doesn't support a claim, say so honestly."
        )

        data_section = ""
        if context:
            import json
            data_section = f"\n\n--- DATA CONTEXT ---\n{json.dumps(context, indent=2, default=str)}\n--- END DATA ---\n"

        full_prompt = f"{system_instruction}{data_section}\n\nUser question: {prompt}"

        response = self.client.models.generate_content(
            model=self.model,
            contents=full_prompt,
        )
        return response.text
