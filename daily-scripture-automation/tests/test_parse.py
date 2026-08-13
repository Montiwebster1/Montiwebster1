from datetime import date

import pytest
from conftest import read_fixture

from daily_scripture.parse import ExtractionError, find_daily_entry


def test_extracts_full_entry_from_sample_page():
    html = read_fixture("sample_page.html")
    entry = find_daily_entry(html, date(2026, 7, 26))

    assert entry.entry_date == date(2026, 7, 26)
    assert entry.theme_scripture_citation == "Prov. 3:5"
    assert "Trust in Jehovah" in entry.theme_scripture_text
    assert entry.comment_count == 3
    assert "relying on him completely" in entry.comments[0]
    assert entry.publication_reference == "w20.06 12 par. 3"


def test_wording_preserved_exactly_no_paraphrase():
    html = read_fixture("sample_page.html")
    entry = find_daily_entry(html, date(2026, 7, 26))
    assert entry.comments[1] == (
        "This kind of trust grows the more we come to know Jehovah through "
        "his Word and through our own experiences."
    )


def test_navigation_and_script_noise_excluded():
    html = read_fixture("sample_page.html")
    entry = find_daily_entry(html, date(2026, 7, 26))
    joined = " ".join(entry.comments) + entry.theme_scripture_text
    assert "Home" not in joined
    assert "console.log" not in joined
    assert "Terms of Use" not in joined


def test_missing_date_entry_raises():
    html = read_fixture("sample_page.html")
    with pytest.raises(ExtractionError, match="No section heading"):
        find_daily_entry(html, date(2026, 12, 25))


def test_wrong_date_page_does_not_match_requested_date():
    html = read_fixture("wrong_date_page.html")
    with pytest.raises(ExtractionError):
        find_daily_entry(html, date(2026, 7, 26))


def test_missing_scripture_text_or_comments_raises():
    html = read_fixture("missing_comments_page.html")
    with pytest.raises(ExtractionError, match="comment"):
        find_daily_entry(html, date(2026, 7, 26))


def test_nav_only_page_rejected_as_not_content():
    html = read_fixture("nav_only_page.html")
    with pytest.raises(ExtractionError, match="navigation, error, or login"):
        find_daily_entry(html, date(2026, 7, 26))


def test_unexpected_html_structure_change_raises_cleanly():
    html = "<html><body><h1>Sunday, July 26</h1><p>no theme scripture markup</p></body></html>"
    with pytest.raises(ExtractionError):
        find_daily_entry(html, date(2026, 7, 26))
