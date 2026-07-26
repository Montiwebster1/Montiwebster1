"""Configuration loading and strict validation.

All configuration comes from environment variables (optionally loaded from a
local `.env` file via python-dotenv). Nothing here contains a real secret —
only names of the variables that hold secrets elsewhere.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


def _load_env_file() -> None:
    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)


@dataclass
class EmailConfig:
    provider: str = ""
    recipient: str = ""
    email_from: str = ""
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    gmail_refresh_token: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""


@dataclass
class TTSConfig:
    provider: str = ""
    api_key: str = ""
    voice_id: str = ""


@dataclass
class JournalConfig:
    handoff_method: str = "queue"
    project_name: str = "Journal - My Children"
    browser_profile_path: str = ""


@dataclass
class Config:
    tz: str = "America/Chicago"
    source_url: str = "https://wol.jw.org/en/wol/d/r1/lp-e/1102026216"
    email: EmailConfig = field(default_factory=EmailConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    journal: JournalConfig = field(default_factory=JournalConfig)
    repo_root: Path = REPO_ROOT

    @property
    def output_dir(self) -> Path:
        return self.repo_root / "output"

    @property
    def audio_dir(self) -> Path:
        return self.output_dir / "audio"

    @property
    def text_dir(self) -> Path:
        return self.output_dir / "text"

    @property
    def journal_handoff_dir(self) -> Path:
        return self.output_dir / "journal-handoff"

    @property
    def logs_dir(self) -> Path:
        return self.repo_root / "logs"

    @property
    def state_dir(self) -> Path:
        return self.repo_root / "state"


def load_config(*, require_email: bool = False, require_tts: bool = False) -> Config:
    """Load configuration from the environment.

    Validation is intentionally staged: callers that only need to preview or
    test extraction should not be forced to configure email/TTS credentials
    they aren't using yet. `require_email` / `require_tts` opt into stricter
    checks for the commands that actually need those providers.
    """
    _load_env_file()

    cfg = Config(
        tz=os.environ.get("TZ", "America/Chicago"),
        source_url=os.environ.get(
            "SOURCE_URL", "https://wol.jw.org/en/wol/d/r1/lp-e/1102026216"
        ),
        email=EmailConfig(
            provider=os.environ.get("EMAIL_PROVIDER", ""),
            recipient=os.environ.get("RECIPIENT_EMAIL", "montiwebster@gmail.com"),
            email_from=os.environ.get("EMAIL_FROM", ""),
            gmail_client_id=os.environ.get("GMAIL_CLIENT_ID", ""),
            gmail_client_secret=os.environ.get("GMAIL_CLIENT_SECRET", ""),
            gmail_refresh_token=os.environ.get("GMAIL_REFRESH_TOKEN", ""),
            smtp_host=os.environ.get("SMTP_HOST", ""),
            smtp_port=int(os.environ.get("SMTP_PORT", "587") or "587"),
            smtp_username=os.environ.get("SMTP_USERNAME", ""),
            smtp_password=os.environ.get("SMTP_PASSWORD", ""),
        ),
        tts=TTSConfig(
            provider=os.environ.get("TTS_PROVIDER", ""),
            api_key=os.environ.get("TTS_API_KEY", ""),
            voice_id=os.environ.get("TTS_VOICE_ID", ""),
        ),
        journal=JournalConfig(
            handoff_method=os.environ.get("CHATGPT_HANDOFF_METHOD", "queue"),
            project_name=os.environ.get("CHATGPT_PROJECT_NAME", "Journal - My Children"),
            browser_profile_path=os.environ.get("CHATGPT_BROWSER_PROFILE_PATH", ""),
        ),
    )

    errors: list[str] = []

    if not cfg.email.recipient:
        errors.append("RECIPIENT_EMAIL is not set.")

    if require_email:
        provider = cfg.email.provider.lower()
        if provider == "gmail_oauth":
            missing = [
                name
                for name, val in (
                    ("GMAIL_CLIENT_ID", cfg.email.gmail_client_id),
                    ("GMAIL_CLIENT_SECRET", cfg.email.gmail_client_secret),
                    ("GMAIL_REFRESH_TOKEN", cfg.email.gmail_refresh_token),
                )
                if not val
            ]
            if missing:
                errors.append(
                    "EMAIL_PROVIDER=gmail_oauth requires: "
                    + ", ".join(missing)
                    + ". Obtain these via Google Cloud Console OAuth client "
                    "credentials + a one-time authorization flow, then store "
                    "them in .env (never in source control)."
                )
        elif provider == "smtp":
            missing = [
                name
                for name, val in (
                    ("SMTP_HOST", cfg.email.smtp_host),
                    ("SMTP_USERNAME", cfg.email.smtp_username),
                    ("SMTP_PASSWORD", cfg.email.smtp_password),
                    ("EMAIL_FROM", cfg.email.email_from),
                )
                if not val
            ]
            if missing:
                errors.append(
                    "EMAIL_PROVIDER=smtp requires: " + ", ".join(missing) + "."
                )
        else:
            errors.append(
                "EMAIL_PROVIDER must be set to 'gmail_oauth' or 'smtp' to send email. "
                f"Got: {cfg.email.provider!r}"
            )

    if require_tts:
        provider = cfg.tts.provider.lower()
        if provider in ("elevenlabs", "openai", "polly", "google", "azure"):
            if not cfg.tts.api_key:
                errors.append(f"TTS_PROVIDER={provider} requires TTS_API_KEY.")
        elif provider in ("", "local", "pyttsx3"):
            pass  # local engine needs no credentials
        else:
            errors.append(f"Unrecognized TTS_PROVIDER: {cfg.tts.provider!r}")

    if errors:
        raise ConfigError(
            "Configuration validation failed:\n- " + "\n- ".join(errors)
        )

    return cfg
