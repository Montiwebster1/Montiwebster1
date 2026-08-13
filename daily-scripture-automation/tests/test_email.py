from pathlib import Path

from daily_scripture.config import Config, EmailConfig
from daily_scripture.email_sender import _build_message


def test_email_attachment_construction(tmp_path):
    audio = tmp_path / "daily-scripture-2026-07-26.mp3"
    audio.write_bytes(b"fake-mp3-bytes")

    cfg = Config(email=EmailConfig(recipient="montiwebster@gmail.com", email_from="bot@example.com"))
    msg = _build_message(cfg, "Daily Scripture — July 26, 2026", "Good morning,\nbody text", audio)

    assert msg["To"] == "montiwebster@gmail.com"
    assert msg["Subject"] == "Daily Scripture — July 26, 2026"
    assert msg.get_body().get_content().startswith("Good morning,")

    attachments = list(msg.iter_attachments())
    assert len(attachments) == 1
    assert attachments[0].get_filename() == "daily-scripture-2026-07-26.mp3"
    assert attachments[0].get_content() == b"fake-mp3-bytes"


def test_email_from_falls_back_to_smtp_username(tmp_path):
    audio = tmp_path / "a.mp3"
    audio.write_bytes(b"x")
    cfg = Config(email=EmailConfig(recipient="m@example.com", smtp_username="sender@example.com"))
    msg = _build_message(cfg, "subj", "body", audio)
    assert msg["From"] == "sender@example.com"
