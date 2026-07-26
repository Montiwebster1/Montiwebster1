"""Turn a DailyEntry into a natural spoken script and a written journal doc."""
from __future__ import annotations

import re

from .parse import DailyEntry

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_URL_RE = re.compile(r"https?://\S+")
_WHITESPACE_RE = re.compile(r"\s+")


def clean_for_speech(text: str) -> str:
    """Strip HTML/URLs/extra whitespace so nothing gets read aloud verbatim."""
    text = _HTML_TAG_RE.sub("", text)
    text = _URL_RE.sub("", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def format_full_date(entry_date) -> str:
    return entry_date.strftime("%B %-d, %Y") if hasattr(entry_date, "strftime") else str(entry_date)


def build_spoken_script(entry: DailyEntry) -> str:
    """Build the exact spoken structure required by the automation spec."""
    full_date = format_full_date(entry.entry_date)
    citation = clean_for_speech(entry.theme_scripture_citation)
    scripture = clean_for_speech(entry.theme_scripture_text)
    comments = [clean_for_speech(c) for c in entry.comments]

    lines = [
        f"Daily scripture for {full_date}.",
        citation + ".",
        scripture,
        "",  # brief pause between scripture and comments
        "Comments.",
        " ".join(comments),
        "End of today's daily scripture.",
    ]
    return "\n\n".join(line for line in lines if line != "").strip()


def build_journal_markdown(entry: DailyEntry, source_url: str) -> str:
    """Format the structured journal entry per the required output template."""
    full_date = format_full_date(entry.entry_date)
    citation = clean_for_speech(entry.theme_scripture_citation)
    scripture = clean_for_speech(entry.theme_scripture_text)
    comments_block = "\n\n".join(clean_for_speech(c) for c in entry.comments)

    return f"""# Daily Scripture Journal Entry
**Date:** {full_date}
**Theme Scripture:** {citation}
## Scripture Text
{scripture}
## Daily Comments
{comments_block}
## Source
Watchtower ONLINE LIBRARY
{source_url}
## Instruction
Process this daily entry according to all instructions configured in the project "Journal - My Children." Do not disregard, replace, or reinterpret the project instructions.
"""


def build_email_body(entry: DailyEntry, source_url: str, *, journal_submitted: bool) -> str:
    full_date = format_full_date(entry.entry_date)
    citation = clean_for_speech(entry.theme_scripture_citation)

    if journal_submitted:
        journal_line = (
            'The written content has also been submitted to the '
            '"Journal - My Children" project for processing.'
        )
    else:
        journal_line = (
            "The written journal entry was prepared, but automatic "
            'submission to the "Journal - My Children" project requires an '
            "authenticated ChatGPT integration."
        )

    return f"""Good morning,
Attached is the daily scripture and comments for {full_date}.
Theme scripture: {citation}
{journal_line}
Source:
{source_url}
"""
