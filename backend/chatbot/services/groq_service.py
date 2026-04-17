import os
from groq import Groq
from django.conf import settings

class GroqService:
    def __init__(self):
        self.api_key = getattr(settings, "GROQ_API_KEY", None) or os.getenv("GROQ_API_KEY")
        self.model = getattr(settings, "GROQ_MODEL", "llama3-70b-8192")
        if not self.api_key:
            # Fallback for dev environment without settings loaded yet
            print("WARNING: GROQ_API_KEY not found in settings, checking env directly.")
            self.api_key = os.getenv("GROQ_API_KEY")
            
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not set.")
            
        self.client = Groq(api_key=self.api_key)

    def chat(self, messages, temperature=0.7, max_tokens=4096):
        """
        Standard chat completion.
        messages = [{"role": "user", "content": "..."}]
        """
        try:
            completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"Groq API Error: {e}")
            raise e

    def generate_content(self, prompt: str, max_tokens=4096) -> str:
        """
        Simple text generation, mimicking some of the genai behavior for easy refactoring.
        """
        return self.chat([{"role": "user", "content": prompt}], max_tokens=max_tokens)
