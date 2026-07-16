from app.services.ai_service import AIService
from unittest.mock import patch

def test_ai_service_unconfigured():
    service = AIService("none", "")
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

    service = AIService("openai", "key", "https://gateway.example/v1", "gateway-model")
    with patch("urllib.request.urlopen", return_value=Response()) as request:
        assert service.analyze_project("test") == "ok"

    called_request = request.call_args.args[0]
    assert called_request.full_url == "https://gateway.example/v1/chat/completions"
    assert b'"model": "gateway-model"' in called_request.data
    assert called_request.get_header("User-agent") == "ProjectOS/1.0"


def test_openai_collects_server_sent_event_stream() -> None:
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return None

        def __iter__(self):
            return iter(
                [
                    b'data: {"choices":[{"delta":{"content":"Hel"}}]}\n',
                    b'data: {"choices":[{"delta":{"content":"lo"}}]}\n',
                    b'data: [DONE]\n',
                ]
            )

    service = AIService("openai", "key", "https://gateway.example/v1", "gateway-model", streaming=True)
    with patch("urllib.request.urlopen", return_value=Response()) as request:
        assert service.analyze_project("test") == "Hello"

    assert b'"stream": true' in request.call_args.args[0].data
    assert request.call_args.args[0].get_header("Accept") == "text/event-stream"
