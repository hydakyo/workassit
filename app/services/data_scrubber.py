"""Remove common secrets and network identifiers before cloud AI requests."""

import re


class DataScrubber:
    """Conservatively redacts information that should not leave the local workspace."""

    _REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
        (re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[^\s]+"), r"\1[REDACTED]"),
        (re.compile(r"(?i)(api[_ -]?key\s*[:=]\s*)[^\s,;]+"), r"\1[REDACTED]"),
        (re.compile(r"(?i)(password\s*[:=]\s*)[^\s,;]+"), r"\1[REDACTED]"),
        (re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"), "[REDACTED_API_KEY]"),
        (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[REDACTED_IP]"),
        (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[REDACTED_EMAIL]"),
    )

    def scrub(self, text: str) -> str:
        """Return text with common credentials and personal/network identifiers redacted."""
        cleaned = text
        for pattern, replacement in self._REPLACEMENTS:
            cleaned = pattern.sub(replacement, cleaned)
        return cleaned
