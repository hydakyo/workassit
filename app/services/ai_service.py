import json
import urllib.request
import urllib.error
import logging
from typing import Iterable, Optional
from urllib.parse import urlparse

from app.config.settings import AI_PROVIDER_GEMINI, AI_PROVIDER_NONE, AI_PROVIDER_OPENAI

logger = logging.getLogger(__name__)


class AIService:
    def __init__(
        self,
        provider: str,
        api_key: str,
        base_url: str = "",
        model: str = "gpt-4o-mini",
        streaming: bool = False,
    ) -> None:
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model or "gpt-4o-mini"
        self.streaming = streaming

    def analyze_project(self, prompt_text: str) -> Optional[str]:
        provider = self.provider.strip().casefold()
        if provider == AI_PROVIDER_NONE or not self.api_key:
            return "AI is not configured."

        if provider == AI_PROVIDER_GEMINI:
            return self._call_gemini(prompt_text)
        if provider == AI_PROVIDER_OPENAI:
            return self._call_openai(prompt_text)

        return "Unsupported AI Provider."

    def _call_gemini(self, prompt: str) -> Optional[str]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"
        data = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                result = json.loads(response.read().decode("utf-8"))
                # Extract text
                candidates = result.get("candidates", [])
                if candidates:
                    content = candidates[0].get("content", {})
                    parts = content.get("parts", [])
                    if parts:
                        return str(parts[0].get("text", ""))
                return "No response generated."
        except urllib.error.URLError as e:
            logger.error("Gemini API request failed: %s", e)
            return f"Error: API request failed. Check API Key and network. ({e})"

    def _call_openai(self, prompt: str) -> Optional[str]:
        url = f"{self.base_url or 'https://api.openai.com/v1'}/chat/completions"
        parsed_url = urlparse(url)
        if parsed_url.scheme != "https" or not parsed_url.netloc:
            return "Error: OpenAI endpoint must be a valid HTTPS URL."
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": self.streaming,
        }
        
        req = urllib.request.Request(
            url, 
            data=json.dumps(data).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "text/event-stream" if self.streaming else "application/json",
                "User-Agent": "ProjectOS/1.0",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                if self.streaming:
                    return self._parse_openai_stream(response)
                result = json.loads(response.read().decode("utf-8"))
                choices = result.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    return str(message.get("content", ""))
                return "No response generated."
        except urllib.error.URLError as e:
            logger.error("OpenAI API request failed: %s", e)
            return f"Error: API request failed. Check API Key and network. ({e})"

    def _parse_openai_stream(self, response: Iterable[bytes]) -> str:
        """Collect OpenAI-compatible Server-Sent Event content chunks into a final response."""
        content_parts: list[str] = []
        for raw_line in response:
            line = raw_line.decode("utf-8").strip()
            if not line.startswith("data:"):
                continue
            data = line.removeprefix("data:").strip()
            if data == "[DONE]":
                break
            try:
                event = json.loads(data)
                choices = event.get("choices", [])
                if choices:
                    delta = choices[0].get("delta", {})
                    content = delta.get("content")
                    if isinstance(content, str):
                        content_parts.append(content)
            except json.JSONDecodeError:
                logger.warning("Ignored malformed OpenAI stream event.")
        return "".join(content_parts) or "No response generated."
