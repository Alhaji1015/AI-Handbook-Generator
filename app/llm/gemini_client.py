import os
from urllib import response
from google import genai

class GeminiClient:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Missing GEMINI_API_KEY in .env")

        self.client = genai.Client(api_key=api_key)
        self.model = os.getenv("GEMINI_CHAT_MODEL", "gemini-1.5-pro")

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.2,
        max_tokens: int = 1000,
    ):
        """
        messages format:
        [
          {"role":"system","content":"..."},
          {"role":"user","content":"..."}
        ]
        """

        # Flatten conversation into prompt text
        prompt = ""
        for m in messages:
            role = m["role"].upper()
            prompt += f"{role}: {m['content']}\n"

        resp = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            },
        )

        return resp.text or ""