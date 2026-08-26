"""Gemini LLM provider implementation with multi-tier failover and direct REST support."""
import os
import json
import logging
import httpx
from ai.provider import LLMProvider

logger = logging.getLogger("skillsetu.ai.gemini")

MODELS = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]


class GeminiProvider(LLMProvider):
    """Robust Google Gemini provider supporting Direct REST HTTP, google-genai, and google.generativeai."""

    def __init__(self):
        self.api_key = self._resolve_api_key()
        self.client = None
        self.model = "gemini-2.0-flash"
        self._sdk = None

        if not self.api_key:
            logger.info("[GeminiProvider] No GEMINI_API_KEY or GOOGLE_API_KEY detected in runtime environment.")
            return

        # Initialize SDK client if available, else will use direct REST via httpx
        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
            self._sdk = "google-genai"
            logger.info("[GeminiProvider] Initialized google-genai SDK.")
        except Exception:
            try:
                import google.generativeai as genai_legacy
                genai_legacy.configure(api_key=self.api_key)
                self.client = genai_legacy
                self._sdk = "google-generativeai"
                logger.info("[GeminiProvider] Initialized google.generativeai SDK.")
            except Exception:
                self.client = "httpx-rest"
                self._sdk = "httpx-rest"
                logger.info("[GeminiProvider] Initialized direct REST client.")

    def _resolve_api_key(self) -> str:
        key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
        if not key:
            try:
                from app.config import settings
                key = settings.gemini_api_key or ""
            except Exception:
                pass
        return key.strip().strip("'\"")

    async def generate(self, prompt: str, context: dict | None = None) -> str:
        if not self.api_key:
            raise RuntimeError("Gemini API key is not configured in backend environment")

        system_instruction = (
            "You are SkillSetu AI Copilot, the official labour-market intelligence and curriculum-alignment assistant for Maharashtra, India. "
            "You provide evidence-based insights for Government, Institutes, Students, and Employers. "
            "Ground your answer in the provided data context when applicable. "
            "Be concise, clear, and actionable."
        )

        data_section = ""
        if context:
            data_section = f"\n\n--- MAHARASHTRA LABOUR-MARKET DATA CONTEXT ---\n{json.dumps(context, indent=2, default=str)}\n--- END DATA CONTEXT ---\n"

        full_prompt = f"{system_instruction}{data_section}\n\nUser Question: {prompt}"

        last_error = None

        # Strategy 1: Direct Async REST Call via httpx (Bypasses all SDK version incompatibilities)
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            for model_name in MODELS:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
                    payload = {
                        "contents": [
                            {
                                "parts": [
                                    {"text": full_prompt}
                                ]
                            }
                        ]
                    }
                    response = await http_client.post(url, json=payload, headers={"Content-Type": "application/json"})
                    if response.status_code == 200:
                        res_json = response.json()
                        text = res_json.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        if text:
                            self.model = model_name
                            logger.info(f"[GeminiProvider] Successfully generated response via REST (model: {model_name})")
                            return text
                    else:
                        err_body = response.text
                        logger.warning(f"[GeminiProvider] REST API with model {model_name} returned status {response.status_code}: {err_body}")
                        last_error = f"HTTP {response.status_code}: {err_body}"
                except Exception as e:
                    logger.warning(f"[GeminiProvider] REST attempt with {model_name} failed: {e}")
                    last_error = str(e)

        # Strategy 2: Native google-genai SDK if REST failed
        if self._sdk == "google-genai" and self.client:
            for model_name in MODELS:
                try:
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=full_prompt,
                    )
                    if response and response.text:
                        self.model = model_name
                        logger.info(f"[GeminiProvider] Successfully generated response via google-genai SDK ({model_name})")
                        return response.text
                except Exception as e:
                    logger.warning(f"[GeminiProvider] google-genai SDK with {model_name} failed: {e}")
                    last_error = str(e)

        # Strategy 3: Legacy google.generativeai SDK
        if self._sdk == "google-generativeai" and self.client:
            for model_name in ["gemini-1.5-flash", "gemini-pro"]:
                try:
                    gen_model = self.client.GenerativeModel(model_name)
                    response = gen_model.generate_content(full_prompt)
                    if response and response.text:
                        self.model = model_name
                        logger.info(f"[GeminiProvider] Successfully generated response via google.generativeai ({model_name})")
                        return response.text
                except Exception as e:
                    logger.warning(f"[GeminiProvider] google.generativeai with {model_name} failed: {e}")
                    last_error = str(e)

        raise RuntimeError(f"All Gemini generation strategies failed. Last error: {last_error}")
