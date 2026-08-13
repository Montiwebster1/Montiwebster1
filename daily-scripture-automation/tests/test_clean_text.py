from datetime import date

from daily_scripture.clean_text import (
    build_email_body,
    build_journal_markdown,
    build_spoken_script,
    clean_for_speech,
)
from daily_scripture.parse import DailyEntry


def make_entry():
    return DailyEntry(
        entry_date=date(2026, 7, 26),
        date_heading_text="Sunday, July 26",
        theme_scripture_citation="Prov. 3:5",
        theme_scripture_text="Trust in Jehovah with all your heart.",
        comments=[
            "Trusting in Jehovah means relying on him completely.",
            "This kind of trust grows over time.",
        ],
        publication_reference="w20.06 12 par. 3",
    )


def test_clean_for_speech_strips_html_and_urls():
    dirty = "<p>See <a href='https://wol.jw.org/x'>this link</a> https://wol.jw.org/y now</p>"
    cleaned = clean_for_speech(dirty)
    assert "<" not in cleaned
    assert "http" not in cleaned
    assert "this link" in cleaned
    assert "now" in cleaned


def test_clean_for_speech_collapses_whitespace():
    assert clean_for_speech("a   b\n\nc\t d") == "a b c d"


def test_spoken_script_structure_order():
    script = build_spoken_script(make_entry())
    lines = [l for l in script.split("\n\n") if l.strip()]
    assert lines[0] == "Daily scripture for July 26, 2026."
    assert lines[1] == "Prov. 3:5."
    assert lines[2] == "Trust in Jehovah with all your heart."
    assert lines[3] == "Comments."
    assert "relying on him completely" in lines[4]
    assert lines[-1] == "End of today's daily scripture."


def test_journal_markdown_matches_required_template():
    md = build_journal_markdown(make_entry(), "https://wol.jw.org/en/wol/d/r1/lp-e/1102026216")
    assert "# Daily Scripture Journal Entry" in md
    assert "**Date:** July 26, 2026" in md
    assert "**Theme Scripture:** Prov. 3:5" in md
    assert "## Scripture Text" in md
    assert "## Daily Comments" in md
    assert "## Source" in md
    assert "## Instruction" in md
    assert "Journal - My Children" in md


def test_email_body_pending_vs_submitted_language():
    entry = make_entry()
    pending = build_email_body(entry, "https://x", journal_submitted=False)
    submitted = build_email_body(entry, "https://x", journal_submitted=True)
    assert "requires an authenticated ChatGPT integration" in pending
    assert "has also been submitted" in submitted
