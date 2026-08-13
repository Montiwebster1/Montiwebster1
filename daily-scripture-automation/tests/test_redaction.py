from daily_scripture.logging_setup import redact


def test_redacts_api_key():
    assert "sk-secretvalue" not in redact("api_key=sk-secretvalue was used")


def test_redacts_refresh_token():
    msg = redact("refresh_token: 1//abc123XYZ sent to gmail")
    assert "1//abc123XYZ" not in msg
    assert "[REDACTED]" in msg


def test_redacts_password():
    assert "hunter2" not in redact("password=hunter2")


def test_redacts_bearer_token():
    assert "abcdef.ghijkl" not in redact("Authorization header: Bearer abcdef.ghijkl")


def test_leaves_non_secret_text_untouched():
    msg = "Extraction OK: date=2026-07-26 comments=3"
    assert redact(msg) == msg
