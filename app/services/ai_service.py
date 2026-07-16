import json
import urllib.request
import urllib.error
import logging
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class AIService:
    def __init__(
        self,
        provider: str,
        api_key: str,
        base_url: str = "",
        model: str = "gpt-4o-mini",
    ) -> None:
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model or "gpt-4o-mini"

    def analyze_project(self, prompt_text: str) -> Optional[str]:
        if self.provider == "None" or not self.api_key:
            return "AI is not configured."
            
        if self.provider == "Gemini":
            return self._call_gemini(prompt_text)
        if self.provider == "OpenAI":
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
            headers={"Content-Type": "application/json"}
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
            logger.error(f"Gemini API request failed: {e}")
            return f"Error: API request failed. Check API Key and network. ({e})"
            
    def _call_openai(self, prompt: str) -> Optional[str]:
        url = f"{self.base_url or 'https://api.openai.com/v1'}/chat/completions"
        parsed_url = urlparse(url)
        if parsed_url.scheme != "https" or not parsed_url.netloc:
            return "Error: OpenAI endpoint must be a valid HTTPS URL."
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        req = urllib.request.Request(
            url, 
            data=json.dumps(data).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                result = json.loads(response.read().decode("utf-8"))
                choices = result.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    return str(message.get("content", ""))
                return "No response generated."
        except urllib.error.URLError as e:
            logger.error(f"OpenAI API request failed: {e}")
            return f"Error: API request failed. Check API Key and network. ({e})"
