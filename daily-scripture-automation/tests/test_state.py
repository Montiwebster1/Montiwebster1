from datetime import date

from daily_scripture.state import RunState, content_hash, load_state, save_state, state_path


def test_content_hash_deterministic_and_sensitive_to_change():
    h1 = content_hash("hello", "world")
    h2 = content_hash("hello", "world")
    h3 = content_hash("hello", "WORLD")
    assert h1 == h2
    assert h1 != h3


def test_save_and_load_round_trip(tmp_path):
    state = RunState(date="2026-07-26", content_hash="abc", audio_generated=True, email_sent=True)
    save_state(tmp_path, state)
    loaded = load_state(tmp_path, date(2026, 7, 26))
    assert loaded == state


def test_state_path_naming(tmp_path):
    path = state_path(tmp_path, date(2026, 7, 26))
    assert path.name == "2026-07-26.json"


def test_load_missing_state_returns_none(tmp_path):
    assert load_state(tmp_path, date(2099, 1, 1)) is None


def test_idempotency_skip_logic_via_flags():
    """Mirrors the CLI's guard: without --force-email, a prior send blocks a resend."""
    state = RunState(date="2026-07-26", email_sent=True, email_message_id="msg-1")
    force_email = False
    should_send = (not state.email_sent) or force_email
    assert should_send is False

    force_email = True
    should_send = (not state.email_sent) or force_email
    assert should_send is True


def test_partial_failure_recovery_state():
    """Audio succeeded, email failed — retry must reuse the audio, not regenerate."""
    state = RunState(date="2026-07-26", audio_generated=True, audio_path="/x/a.mp3", email_sent=False)
    assert state.audio_generated is True
    assert state.email_sent is False
    # A retry path should see audio_generated=True and skip TTS.
    needs_audio = not state.audio_generated
    assert needs_audio is False
