"""Structured logging to logs/daily-scripture-YYYY-MM-DD.log with secret redaction."""
from __future__ import annotations

import logging
import re
from datetime import date
from pathlib import Path

_SECRET_PATTERNS = [
    re.compile(r"(api[_-]?key\s*[:=]\s*)([^\s,;\"']+)", re.IGNORECASE),
    re.compile(r"(refresh[_-]?token\s*[:=]\s*)([^\s,;\"']+)", re.IGNORECASE),
    re.compile(r"(access[_-]?token\s*[:=]\s*)([^\s,;\"']+)", re.IGNORECASE),
    re.compile(r"(password\s*[:=]\s*)([^\s,;\"']+)", re.IGNORECASE),
    re.compile(r"(client[_-]?secret\s*[:=]\s*)([^\s,;\"']+)", re.IGNORECASE),
    re.compile(r"(Bearer\s+)([A-Za-z0-9\-_.]+)"),
    re.compile(r"(Authorization:\s*)(.+)", re.IGNORECASE),
]


def redact(message: str) -> str:
    redacted = message
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub(lambda m: m.group(1) + "[REDACTED]", redacted)
    return redacted


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(str(record.msg))
        if record.args:
            record.args = tuple(
                redact(str(a)) if isinstance(a, str) else a for a in record.args
            )
        return True


def setup_logging(logs_dir: Path, entry_date: date, *, level: int = logging.INFO) -> Path:
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"daily-scripture-{entry_date.isoformat()}.log"

    root = logging.getLogger("daily_scripture")
    root.setLevel(level)
    root.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s", datefmt="%Y-%m-%dT%H:%M:%S%z"
    )

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.addFilter(RedactingFilter())
    root.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.addFilter(RedactingFilter())
    root.addHandler(console_handler)

    return log_path
