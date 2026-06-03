import httpx

from app.services.model_registry import redact_url, safe_http_error


def test_redact_url_masks_sensitive_query_params():
    url = "https://generativelanguage.googleapis.com/v1beta/models?key=AIza_TEST_SECRET&foo=bar&token=abc123"

    redacted = redact_url(url)

    assert "AIza_TEST_SECRET" not in redacted
    assert "abc123" not in redacted
    assert "key=%5BREDACTED%5D" in redacted or "key=[REDACTED]" in redacted
    assert "token=%5BREDACTED%5D" in redacted or "token=[REDACTED]" in redacted
    assert "foo=bar" in redacted


def test_safe_http_error_does_not_leak_query_api_key():
    request = httpx.Request(
        "GET",
        "https://generativelanguage.googleapis.com/v1beta/models?key=AIza_TEST_SECRET",
    )
    response = httpx.Response(400, request=request)
    exc = httpx.HTTPStatusError("boom", request=request, response=response)

    formatted = safe_http_error(exc)

    assert "AIza_TEST_SECRET" not in formatted
    assert "key=" in formatted
    assert "%5BREDACTED%5D" in formatted or "[REDACTED]" in formatted
    assert "status=400" in formatted
