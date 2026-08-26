from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract interface for LLM providers.

    Implementations: GeminiProvider (primary), DemoProvider (fallback).
    Adding Groq later = create GroqProvider implementing this interface.
    """

    @abstractmethod
    async def generate(self, prompt: str, context: dict | None = None) -> str:
        """Generate a response given a prompt and optional structured context.

        Args:
            prompt: The user's question or instruction.
            context: Structured data dict to ground the response (skills, gaps, etc.)

        Returns:
            The generated text response.
        """
        ...
