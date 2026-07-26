"""Fallback extraction path: ask ChatGPT (OpenAI Responses API + web_search
tool) to fetch and read the source page when direct HTTP fetch/parse fails.

This is a fallback, not the primary path. `main.py` tries `fetch.py` +
`parse.py` (direct HTTP + HTML parsing) first, because that's the least
brittle, lowest-cost method per the spec's extraction-reliability ordering.
It only calls into this module when that fails AND
EXTRACTION_FALLBACK=openai is configured with an OPENAI_API_KEY.

The model is instructed to browse the live page, locate the section for the
requested date, and return ONLY the requested fields as JSON — preserving
exact wording, not summarizing. The same DailyEntry structural validation
used for the HTML path applies here too (all required fields must be
non-empty, date must match).
"""
from __future__ import annotations

import json
import logging
import re
import time
from datetime import date

from .parse import DailyEntry, ExtractionError

logger = logging.getLogger("daily_scripture.openai_extract")

MAX_ATTEMPTS = 3
BACKOFF_SECONDS = (2, 4, 8)

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)

_SYSTEM_INSTRUCTIONS = """You are a precise data-extraction tool, not a writer.
Fetch the given URL and locate the section for the exact calendar date given.
Return ONLY a single JSON object (no markdown fences, no commentary) with
these exact keys:
  date_heading_text   - the heading text as shown on the page (e.g. "Sunday, July 26")
  theme_scripture_citation - the scripture citation only (e.g. "Prov. 3:5")
  theme_scripture_text     - the scripture text only, verbatim
  comments - a JSON array of strings, one per comment/explanatory paragraph,
             in original order, verbatim (do not merge, summarize, or
             paraphrase; do not include the publication reference here)
  publication_reference - the cited publication/source reference shown with
             the entry (e.g. "w20.06 12 par. 3"), or "" if none is shown

Rules:
- Preserve wording EXACTLY as published. Never summarize, paraphrase,
  interpret, embellish, or add commentary of your own.
- Do not include navigation text, button labels, or URLs in any field.
- If you cannot find an entry matching the requested date, return
  {"error": "not_found"} instead.
"""


class OpenAIExtractionError(ExtractionError):
    pass


def _call_openai(source_url: str, target_date: date, api_key: str) -> dict:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    prompt = (
        f"{_SYSTEM_INSTRUCTIONS}\n\n"
        f"URL: {source_url}\n"
        f"Requested date: {target_date.strftime('%A, %B %-d, %Y')}"
    )

    response = client.responses.create(
        model="gpt-4.1",
        tools=[{"type": "web_search"}],
        input=prompt,
    )
    text = response.output_text.strip()
    match = _JSON_BLOCK_RE.search(text)
    if not match:
        raise OpenAIExtractionError(
            f"OpenAI extraction fallback did not return JSON. Raw output: {text[:200]!r}"
        )
    return json.loads(match.group(0))


def find_daily_entry_via_openai(
    source_url: str, target_date: date, api_key: str
) -> DailyEntry:
    """Same contract as parse.find_daily_entry, sourced via ChatGPT web browsing."""
    if not api_key:
        raise OpenAIExtractionError(
            "EXTRACTION_FALLBACK=openai requires OPENAI_API_KEY."
        )

    last_error: Exception | None = None
    data: dict | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            data = _call_openai(source_url, target_date, api_key)
            break
        except Exception as exc:  # noqa: BLE001 - SDK raises many types
            last_error = exc
            logger.warning(
                "OpenAI extraction attempt %d/%d failed: %s", attempt, MAX_ATTEMPTS, exc
            )
            if attempt < MAX_ATTEMPTS:
                time.sleep(BACKOFF_SECONDS[min(attempt - 1, len(BACKOFF_SECONDS) - 1)])
    if data is None:
        raise OpenAIExtractionError(
            f"OpenAI extraction fallback failed after {MAX_ATTEMPTS} attempts: {last_error}"
        )

    if data.get("error") == "not_found":
        raise OpenAIExtractionError(
            f"ChatGPT could not find an entry for {target_date.isoformat()} on {source_url}."
        )

    citation = (data.get("theme_scripture_citation") or "").strip()
    scripture_text = (data.get("theme_scripture_text") or "").strip()
    comments = [c.strip() for c in (data.get("comments") or []) if c and c.strip()]
    date_heading_text = (data.get("date_heading_text") or "").strip()
    publication_reference = (data.get("publication_reference") or "").strip()

    if not citation:
        raise OpenAIExtractionError("OpenAI extraction: theme scripture citation missing.")
    if not scripture_text:
        raise OpenAIExtractionError("OpenAI extraction: theme scripture text missing.")
    if not comments:
        raise OpenAIExtractionError("OpenAI extraction: no comment paragraphs returned.")

    return DailyEntry(
        entry_date=target_date,
        date_heading_text=date_heading_text or target_date.isoformat(),
        theme_scripture_citation=citation,
        theme_scripture_text=scripture_text,
        comments=comments,
        publication_reference=publication_reference,
    )
