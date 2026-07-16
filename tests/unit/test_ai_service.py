from app.services.ai_service import AIService

def test_ai_service_unconfigured():
    service = AIService("None", "")
    assert service.analyze_project("test") == "AI is not configured."

def test_ai_service_unsupported():
    service = AIService("Unknown", "key")
    assert service.analyze_project("test") == "Unsupported AI Provider."
