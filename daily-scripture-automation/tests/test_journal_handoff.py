from datetime import date

from daily_scripture.config import Config, JournalConfig
from daily_scripture.journal import submit_journal_entry


def test_queue_fallback_when_no_integration_configured(tmp_path):
    cfg = Config(repo_root=tmp_path, journal=JournalConfig(handoff_method="queue"))
    result = submit_journal_entry(cfg, date(2026, 7, 26), "# entry body")

    assert result.status == "pending"
    assert "authenticated ChatGPT" in result.reason
    saved_path = tmp_path / "output" / "journal-handoff" / "2026-07-26.md"
    assert saved_path.exists()
    assert saved_path.read_text() == "# entry body"
    assert result.reference == str(saved_path)


def test_api_method_without_integration_falls_back_to_queue(tmp_path):
    cfg = Config(repo_root=tmp_path, journal=JournalConfig(handoff_method="api"))
    result = submit_journal_entry(cfg, date(2026, 7, 26), "# entry body")
    assert result.status == "pending"


def test_browser_method_without_profile_falls_back_to_queue(tmp_path):
    cfg = Config(
        repo_root=tmp_path,
        journal=JournalConfig(handoff_method="browser", browser_profile_path=""),
    )
    result = submit_journal_entry(cfg, date(2026, 7, 26), "# entry body")
    assert result.status == "pending"
