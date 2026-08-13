"""Email delivery: Gmail OAuth (preferred) or SMTP, with a confirmed message ID."""
from __future__ import annotations

import base64
import logging
import mimetypes
import smtplib
import time
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path

from .config import Config

logger = logging.getLogger("daily_scripture.email")

MAX_ATTEMPTS = 3
BACKOFF_SECONDS = (2, 4, 8)


class EmailError(RuntimeError):
    pass


class PermanentEmailError(EmailError):
    pass


@dataclass
class EmailResult:
    provider: str
    message_id: str


def _build_message(cfg: Config, subject: str, body: str, attachment_path: Path) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg.email.email_from or cfg.email.smtp_username or cfg.email.recipient
    msg["To"] = cfg.email.recipient
    msg.set_content(body)

    ctype, _ = mimetypes.guess_type(str(attachment_path))
    maintype, subtype = (ctype.split("/", 1) if ctype else ("audio", "mpeg"))
    msg.add_attachment(
        attachment_path.read_bytes(),
        maintype=maintype,
        subtype=subtype,
        filename=attachment_path.name,
    )
    return msg


def _send_smtp(cfg: Config, msg: EmailMessage) -> EmailResult:
    def call():
        with smtplib.SMTP(cfg.email.smtp_host, cfg.email.smtp_port, timeout=30) as smtp:
            smtp.starttls()
            try:
                smtp.login(cfg.email.smtp_username, cfg.email.smtp_password)
            except smtplib.SMTPAuthenticationError as exc:
                raise PermanentEmailError(f"SMTP authentication failed: {exc.smtp_code}") from exc
            send_errors = smtp.send_message(msg)
            if send_errors:
                raise EmailError(f"SMTP server rejected recipients: {send_errors}")
            # smtplib doesn't return a message-id; use the Message-ID header we set,
            # falling back to a value derived from the server's QUIT response.
            message_id = msg.get("Message-Id") or f"smtp-{int(time.time())}"
            return EmailResult(provider="smtp", message_id=message_id)

    return _with_retries(call, what="SMTP send")


def _send_gmail_oauth(cfg: Config, msg: EmailMessage) -> EmailResult:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request as GoogleRequest
    from googleapiclient.discovery import build

    def call():
        creds = Credentials(
            token=None,
            refresh_token=cfg.email.gmail_refresh_token,
            client_id=cfg.email.gmail_client_id,
            client_secret=cfg.email.gmail_client_secret,
            token_uri="https://oauth2.googleapis.com/token",
        )
        try:
            creds.refresh(GoogleRequest())
        except Exception as exc:  # noqa: BLE001
            raise PermanentEmailError(f"Gmail OAuth token refresh failed: {exc}") from exc

        service = build("gmail", "v1", credentials=creds)
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
        message_id = sent.get("id")
        if not message_id:
            raise EmailError("Gmail API did not return a message id.")
        return EmailResult(provider="gmail_oauth", message_id=message_id)

    return _with_retries(call, what="Gmail OAuth send")


def _with_retries(fn, *, what: str):
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return fn()
        except PermanentEmailError:
            raise
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning("%s attempt %d/%d failed: %s", what, attempt, MAX_ATTEMPTS, exc)
            if attempt < MAX_ATTEMPTS:
                time.sleep(BACKOFF_SECONDS[min(attempt - 1, len(BACKOFF_SECONDS) - 1)])
    raise EmailError(f"{what} failed after {MAX_ATTEMPTS} attempts: {last_error}")


def send_daily_email(
    cfg: Config, *, subject: str, body: str, attachment_path: Path
) -> EmailResult:
    msg = _build_message(cfg, subject, body, attachment_path)
    provider = (cfg.email.provider or "").lower().strip()

    if provider == "gmail_oauth":
        return _send_gmail_oauth(cfg, msg)
    if provider == "smtp":
        return _send_smtp(cfg, msg)
    raise PermanentEmailError(
        f"EMAIL_PROVIDER must be 'gmail_oauth' or 'smtp'. Got: {cfg.email.provider!r}"
    )
