"""Fetch the source page with bounded retries and a clear user agent."""
from __future__ import annotations

import logging
import time

import requests

logger = logging.getLogger("daily_scripture.fetch")

USER_AGENT = (
    "DailyScriptureAudioJournal/1.0 "
    "(+personal automation; contact: montiwebster@gmail.com)"
)

MAX_ATTEMPTS = 3
TIMEOUT_SECONDS = 20
BACKOFF_SECONDS = (2, 4, 8)


class FetchError(RuntimeError):
    """Raised when the source page cannot be retrieved after retries."""


class PermanentFetchError(FetchError):
    """Raised for errors that must not be retried (e.g. 401/403/404)."""


_NO_RETRY_STATUS = {401, 403, 404, 410}


def fetch_page(url: str, *, session: requests.Session | None = None) -> str:
    """Fetch `url` and return the response body as text.

    Retries transient network/5xx failures up to MAX_ATTEMPTS times with
    exponential backoff. Does not retry auth/not-found style permanent
    failures.
    """
    sess = session or requests.Session()
    last_error: Exception | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = sess.get(
                url,
                headers={"User-Agent": USER_AGENT, "Accept-Language": "en"},
                timeout=TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            last_error = exc
            logger.warning("Fetch attempt %d/%d failed: %s", attempt, MAX_ATTEMPTS, exc)
        else:
            if response.status_code in _NO_RETRY_STATUS:
                raise PermanentFetchError(
                    f"Source page returned {response.status_code} for {url}; "
                    "not retrying (permanent failure)."
                )
            if response.ok:
                return response.text
            last_error = FetchError(
                f"Source page returned HTTP {response.status_code} for {url}"
            )
            logger.warning(
                "Fetch attempt %d/%d got HTTP %d", attempt, MAX_ATTEMPTS, response.status_code
            )

        if attempt < MAX_ATTEMPTS:
            time.sleep(BACKOFF_SECONDS[min(attempt - 1, len(BACKOFF_SECONDS) - 1)])

    raise FetchError(f"Failed to fetch {url} after {MAX_ATTEMPTS} attempts: {last_error}")
