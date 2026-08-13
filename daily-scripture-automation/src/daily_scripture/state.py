"""Idempotent run-state tracking, one JSON record per date."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path


@dataclass
class RunState:
    date: str
    content_hash: str = ""
    audio_generated: bool = False
    audio_path: str = ""
    email_sent: bool = False
    email_message_id: str = ""
    journal_status: str = "pending"  # submitted | pending | failed
    journal_reference: str = ""
    completed_at: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)


def content_hash(*parts: str) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(part.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def state_path(state_dir: Path, entry_date: date) -> Path:
    return state_dir / f"{entry_date.isoformat()}.json"


def load_state(state_dir: Path, entry_date: date) -> RunState | None:
    path = state_path(state_dir, entry_date)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return RunState(**data)


def save_state(state_dir: Path, state: RunState) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_path(state_dir, date.fromisoformat(state.date))
    path.write_text(state.to_json(), encoding="utf-8")


def mark_completed_now(state: RunState) -> None:
    state.completed_at = datetime.now(timezone.utc).isoformat()
