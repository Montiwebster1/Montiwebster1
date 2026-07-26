import pytest

from daily_scripture.config import Config, EmailConfig, TTSConfig, load_config, ConfigError


def test_require_email_smtp_missing_fields_raises(monkeypatch, tmp_path):
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_USERNAME", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    monkeypatch.delenv("EMAIL_FROM", raising=False)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ConfigError, match="SMTP_HOST"):
        load_config(require_email=True)


def test_require_tts_unrecognized_provider_raises(monkeypatch, tmp_path):
    monkeypatch.setenv("TTS_PROVIDER", "not-a-real-provider")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ConfigError, match="Unrecognized TTS_PROVIDER"):
        load_config(require_tts=True)


def test_no_tts_provider_is_valid_local_fallback(monkeypatch, tmp_path):
    monkeypatch.delenv("TTS_PROVIDER", raising=False)
    monkeypatch.chdir(tmp_path)
    cfg = load_config(require_tts=True)
    assert cfg.tts.provider == ""
