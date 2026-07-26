"""ChatGPT project handoff: Method 1 (API) > Method 2 (browser) > Method 3 (safe queue).

This build ships Method 3 (safe handoff queue) as the working path, because
no official "create a session inside a named ChatGPT project" API exists
today, and this sandboxed session has no authenticated, persistent browser
profile available to drive Method 2. Both hooks are left in place — wired
through `CHATGPT_HANDOFF_METHOD` — so a future run with a real integration
can flip the method without code changes to callers.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .config import Config

logger = logging.getLogger("daily_scripture.journal")

MAX_ATTEMPTS = 2
BACKOFF_SECONDS = (3, 6)


class JournalError(RuntimeError):
    pass


@dataclass
class JournalResult:
    status: str  # "submitted" | "pending" | "failed"
    reference: str
    reason: str = ""


def _queue_path(cfg: Config, entry_date: date) -> Path:
    return cfg.journal_handoff_dir / f"{entry_date.isoformat()}.md"


def _submit_via_queue(cfg: Config, entry_date: date, markdown: str) -> JournalResult:
    cfg.journal_handoff_dir.mkdir(parents=True, exist_ok=True)
    path = _queue_path(cfg, entry_date)
    path.write_text(markdown, encoding="utf-8")
    reason = (
        'No authenticated ChatGPT project integration is configured '
        "(CHATGPT_HANDOFF_METHOD is not 'api' or 'browser', or the "
        "configured method's prerequisites are missing). The structured "
        f"journal entry was saved to {path.relative_to(cfg.repo_root)} for "
        "manual submission."
    )
    logger.info("Journal handoff pending: %s", reason)
    return JournalResult(status="pending", reference=str(path), reason=reason)


def _submit_via_api(cfg: Config, entry_date: date, markdown: str) -> JournalResult:
    raise JournalError(
        "CHATGPT_HANDOFF_METHOD=api was requested, but no official OpenAI/"
        "ChatGPT API for creating a session inside a named ChatGPT *project* "
        "is configured in this environment. Falling back is handled by the "
        "caller."
    )


def _submit_via_browser(cfg: Config, entry_date: date, markdown: str) -> JournalResult:
    if not cfg.journal.browser_profile_path:
        raise JournalError(
            "CHATGPT_HANDOFF_METHOD=browser requires CHATGPT_BROWSER_PROFILE_PATH "
            "to point at an already-authenticated persistent browser profile."
        )

    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    project_name = cfg.journal.project_name

    def call():
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                cfg.journal.browser_profile_path, headless=True
            )
            page = context.new_page()
            try:
                page.goto("https://chatgpt.com/", timeout=30000)
                page.get_by_role("link", name=project_name).click(timeout=15000)
                page.get_by_role("button", name="New chat").click(timeout=15000)
                page.get_by_role("textbox").fill(markdown)
                page.get_by_role("button", name="Send").click(timeout=15000)
                page.wait_for_selector(
                    "[data-message-author-role='assistant']", timeout=60000
                )
                conversation_url = page.url
                return JournalResult(status="submitted", reference=conversation_url)
            except PWTimeout as exc:
                raise JournalError(f"Browser handoff timed out: {exc}") from exc
            finally:
                context.close()

    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return call()
        except JournalError as exc:
            last_error = exc
            logger.warning(
                "Browser journal handoff attempt %d/%d failed: %s",
                attempt, MAX_ATTEMPTS, exc,
            )
            if attempt < MAX_ATTEMPTS:
                time.sleep(BACKOFF_SECONDS[min(attempt - 1, len(BACKOFF_SECONDS) - 1)])
    raise JournalError(f"Browser journal handoff failed: {last_error}")


def submit_journal_entry(cfg: Config, entry_date: date, markdown: str) -> JournalResult:
    method = (cfg.journal.handoff_method or "queue").lower().strip()

    if method == "api":
        try:
            return _submit_via_api(cfg, entry_date, markdown)
        except JournalError as exc:
            logger.warning("API handoff unavailable, falling back to queue: %s", exc)
            return _submit_via_queue(cfg, entry_date, markdown)

    if method == "browser":
        try:
            return _submit_via_browser(cfg, entry_date, markdown)
        except JournalError as exc:
            logger.warning("Browser handoff failed, falling back to queue: %s", exc)
            return _submit_via_queue(cfg, entry_date, markdown)

    return _submit_via_queue(cfg, entry_date, markdown)
