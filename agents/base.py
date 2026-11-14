"""BaseAgent providing core agent structure and safe LLM invocation with fallbacks."""
import os
from typing import Optional
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class BaseAgent:
    """Base class for all agents in the platform."""

    def __init__(self, name: str):
        self.name = name

    def run(self, *args, **kwargs):
        """Execute agent task. Must be implemented by child classes."""
        raise NotImplementedError("Subclasses must implement run()")

    def call_llm(self, prompt: str, fallback_text: str, model_name: str = "gemini-2.5-flash") -> str:
        """
        Safely calls Gemini API. If GEMINI_API_KEY is missing or the call fails,
        returns fallback_text cleanly without crashing.
        """
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key or api_key == "your_gemini_api_key_here":
            return fallback_text

        try:
            # Try google-genai client first
            from google import genai
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            if response and hasattr(response, "text") and response.text:
                return response.text.strip()
            return fallback_text
        except Exception:
            try:
                # Fallback to google.generativeai if available
                import google.generativeai as legacy_genai
                legacy_genai.configure(api_key=api_key)
                model = legacy_genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                if response and hasattr(response, "text") and response.text:
                    return response.text.strip()
            except Exception:
                pass
            return fallback_text
