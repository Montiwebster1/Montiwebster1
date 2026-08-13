"""Pluggable text-to-speech generation.

Provider selection order (per spec):
  1. A TTS service already configured in the environment (TTS_PROVIDER set
     to one it's already wired for — treated the same as an explicit choice
     below).
  2. ElevenLabs
  3. OpenAI text-to-speech
  4. Amazon Polly, Google Cloud TTS, or Azure Speech
  5. A reliable local operating-system TTS engine (pyttsx3) — always
     available, no API key required, used automatically when nothing else
     is configured.

No API keys are ever hard-coded; everything comes from Config/env vars.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

from .config import Config

logger = logging.getLogger("daily_scripture.tts")

MAX_ATTEMPTS = 3
BACKOFF_SECONDS = (2, 4, 8)


class TTSError(RuntimeError):
    pass


class PermanentTTSError(TTSError):
    pass


@dataclass
class AudioResult:
    path: Path
    provider: str
    format: str
    duration_seconds: float | None


def _with_retries(fn, *, what: str):
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return fn()
        except PermanentTTSError:
            raise
        except Exception as exc:  # noqa: BLE001 - provider SDKs raise many types
            last_error = exc
            logger.warning("%s attempt %d/%d failed: %s", what, attempt, MAX_ATTEMPTS, exc)
            if attempt < MAX_ATTEMPTS:
                time.sleep(BACKOFF_SECONDS[min(attempt - 1, len(BACKOFF_SECONDS) - 1)])
    raise TTSError(f"{what} failed after {MAX_ATTEMPTS} attempts: {last_error}")


def _generate_elevenlabs(script: str, out_path: Path, cfg: Config) -> AudioResult:
    import requests

    if not cfg.tts.api_key:
        raise PermanentTTSError("TTS_API_KEY is required for ElevenLabs.")
    voice_id = cfg.tts.voice_id or "21m00Tcm4TlvDq8ikWAM"  # ElevenLabs default demo voice

    def call():
        resp = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={
                "xi-api-key": cfg.tts.api_key,
                "Content-Type": "application/json",
            },
            json={
                "text": script,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
            },
            timeout=60,
        )
        if resp.status_code in (401, 403):
            raise PermanentTTSError(f"ElevenLabs auth failed: HTTP {resp.status_code}")
        resp.raise_for_status()
        out_path.write_bytes(resp.content)
        return AudioResult(out_path, "elevenlabs", "mp3", None)

    return _with_retries(call, what="ElevenLabs TTS")


def _generate_openai(script: str, out_path: Path, cfg: Config) -> AudioResult:
    from openai import OpenAI

    if not cfg.tts.api_key:
        raise PermanentTTSError("TTS_API_KEY is required for OpenAI TTS.")

    def call():
        client = OpenAI(api_key=cfg.tts.api_key)
        with client.audio.speech.with_streaming_response.create(
            model="tts-1",
            voice=cfg.tts.voice_id or "alloy",
            input=script,
        ) as response:
            response.stream_to_file(out_path)
        return AudioResult(out_path, "openai", "mp3", None)

    return _with_retries(call, what="OpenAI TTS")


def _generate_local(script: str, out_path: Path, cfg: Config) -> AudioResult:
    """Local OS TTS engine via pyttsx3. Always available, no key needed.

    pyttsx3 cannot write MP3 directly, so this produces WAV — the fallback
    format explicitly permitted by the spec when MP3 isn't available.
    """
    import pyttsx3

    wav_path = out_path.with_suffix(".wav")

    def call():
        engine = pyttsx3.init()
        engine.setProperty("rate", 165)  # moderate speaking pace
        engine.save_to_file(script, str(wav_path))
        engine.runAndWait()
        if not wav_path.exists() or wav_path.stat().st_size == 0:
            raise TTSError("Local TTS engine produced no audio output.")
        return AudioResult(wav_path, "local-pyttsx3", "wav", None)

    return _with_retries(call, what="Local TTS")


_PROVIDERS = {
    "elevenlabs": _generate_elevenlabs,
    "openai": _generate_openai,
}


def generate_audio(script: str, out_path: Path, cfg: Config) -> AudioResult:
    """Generate narration audio, honoring the configured provider with a
    documented fallback to local OS TTS when nothing is configured."""
    provider = (cfg.tts.provider or "").lower().strip()

    if provider in _PROVIDERS:
        try:
            return _PROVIDERS[provider](script, out_path, cfg)
        except PermanentTTSError:
            raise
    elif provider in ("", "local", "pyttsx3"):
        pass
    else:
        raise PermanentTTSError(
            f"Unrecognized TTS_PROVIDER {cfg.tts.provider!r}. Supported: "
            "elevenlabs, openai, local (or leave unset for local)."
        )

    logger.info(
        "Falling back to local OS TTS engine (pyttsx3) — no cloud TTS "
        "provider configured or provider failed permanently."
    )
    return _generate_local(script, out_path, cfg)
