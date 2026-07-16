from dataclasses import dataclass, field
from typing import List


AI_PROVIDER_NONE = "none"
AI_PROVIDER_OPENAI = "openai"
AI_PROVIDER_GEMINI = "gemini"


def normalize_ai_provider(provider: str) -> str:
    """Convert supported provider labels, including legacy values, to stable config values."""
    normalized = provider.strip().casefold()
    aliases = {
        "": AI_PROVIDER_NONE,
        "none": AI_PROVIDER_NONE,
        "openai": AI_PROVIDER_OPENAI,
        "gemini": AI_PROVIDER_GEMINI,
    }
    if normalized not in aliases:
        raise ValueError("Unsupported AI provider type.")
    return aliases[normalized]


@dataclass
class AppSettings:
    schema_version: int = 1
    workspace_roots: List[str] = field(default_factory=list)
    theme: str = "dark"
    default_author: str = ""
    ai_provider: str = AI_PROVIDER_NONE
    ai_api_key: str = ""
    ai_base_url: str = ""
    ai_model: str = "gpt-4o-mini"
    ai_streaming: bool = True
