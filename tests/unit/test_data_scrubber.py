from app.services.data_scrubber import DataScrubber


def test_scrub_redacts_cloud_sensitive_values() -> None:
    scrubber = DataScrubber()

    result = scrubber.scrub(
        "Authorization: Bearer token-value\n"
        "api_key=abc123\npassword: secret\n"
        "key sk-example_key_12345 IP 10.2.3.4 user@example.com"
    )

    assert "token-value" not in result
    assert "abc123" not in result
    assert "secret" not in result
    assert "sk-example_key_12345" not in result
    assert "10.2.3.4" not in result
    assert "user@example.com" not in result
    assert "[REDACTED_IP]" in result
