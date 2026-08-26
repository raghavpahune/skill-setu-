"""Gemini LLM provider implementation."""
import os
from ai.provider import LLMProvider


class GeminiProvider(LLMProvider):
    """Google Gemini API provider supporting multiple SDK versions & env vars."""

    def __init__(self):
        self.client = None
        self.model = "gemini-2.0-flash"
        self._sdk = None

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
        if not api_key:
            try:
                from app.config import settings
                api_key = settings.gemini_api_key or ""
            except Exception:
                pass

        if not api_key:
            return

        # Attempt modern google-genai SDK first
        try:
            from google import genai
            self.client = genai.Client(api_key=api_key)
            self._sdk = "google-genai"
        except Exception:
            # Fallback to legacy google-generativeai SDK if installed
            try:
                import google.generativeai as genai_legacy
                genai_legacy.configure(api_key=api_key)
                self.client = genai_legacy.GenerativeModel("gemini-1.5-flash")
                self._sdk = "google-generativeai"
            except Exception:
                self.client = None

    async def generate(self, prompt: str, context: dict | None = None) -> str:
        if not self.client:
            raise RuntimeError("Gemini client not initialized — missing API key or genai package")

        system_instruction = (
            "You are SkillSetu AI Copilot, an official labour-market intelligence and curriculum-alignment assistant for Maharashtra, India. "
            "You answer questions about skill demand, skill gaps, curriculum recommendations, "
            "future skill forecasts, industry signals, and career guidance for Government, Institutes, Students, and Employers. "
            "Always ground your answers in the provided data context. "
            "Structure your answers with: 1) Direct Answer, 2) Data Evidence from Maharashtra dataset, 3) Recommended Action. "
            "Cite specific numbers, districts, and evidence. Be concise, actionable, and authoritative."
        )

        data_section = ""
        if context:
            import json
            data_section = f"\n\n--- MAHARASHTRA LABOUR-MARKET DATA CONTEXT ---\n{json.dumps(context, indent=2, default=str)}\n--- END DATA CONTEXT ---\n"

        full_prompt = f"{system_instruction}{data_section}\n\nUser question: {prompt}"

        if self._sdk == "google-genai":
            response = self.client.models.generate_content(
                model=self.model,
                contents=full_prompt,
            )
            return response.text
        elif self._sdk == "google-generativeai":
            response = self.client.generate_content(full_prompt)
            return response.text
        else:
            raise RuntimeError("No active Gemini SDK client initialized")
