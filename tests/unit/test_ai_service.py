from app.services.ai_service import AIService
from unittest.mock import patch

def test_ai_service_unconfigured():
    service = AIService("None", "")
    assert service.analyze_project("test") == "AI is not configured."

def test_ai_service_unsupported():
    service = AIService("Unknown", "key")
    assert service.analyze_project("test") == "Unsupported AI Provider."


def test_openai_requires_https_endpoint() -> None:
    service = AIService("OpenAI", "key", "http://localhost:8080/v1")
    assert service.analyze_project("test") == "Error: OpenAI endpoint must be a valid HTTPS URL."


def test_openai_uses_configured_endpoint_and_model() -> None:
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return None

        def read(self) -> bytes:
            return b'{"choices": [{"message": {"content": "ok"}}]}'

    service = AIService("OpenAI", "key", "https://gateway.example/v1", "gateway-model")
    with patch("urllib.request.urlopen", return_value=Response()) as request:
        assert service.analyze_project("test") == "ok"

    called_request = request.call_args.args[0]
    assert called_request.full_url == "https://gateway.example/v1/chat/completions"
    assert b'"model": "gateway-model"' in called_request.data
