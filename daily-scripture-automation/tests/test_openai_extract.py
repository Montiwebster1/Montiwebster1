import json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from daily_scripture.openai_extract import (
    OpenAIExtractionError,
    find_daily_entry_via_openai,
)


def _fake_response(payload: dict):
    resp = MagicMock()
    resp.output_text = json.dumps(payload)
    return resp


def test_no_api_key_raises_immediately():
    with pytest.raises(OpenAIExtractionError, match="OPENAI_API_KEY"):
        find_daily_entry_via_openai("https://x", date(2026, 7, 26), "")


@patch("daily_scripture.openai_extract._call_openai")
def test_successful_extraction_maps_fields(mock_call):
    mock_call.return_value = {
        "date_heading_text": "Sunday, July 26",
        "theme_scripture_citation": "Prov. 3:5",
        "theme_scripture_text": "Trust in Jehovah with all your heart.",
        "comments": ["Comment one.", "Comment two."],
        "publication_reference": "w20.06 12 par. 3",
    }
    entry = find_daily_entry_via_openai("https://x", date(2026, 7, 26), "sk-test")
    assert entry.theme_scripture_citation == "Prov. 3:5"
    assert entry.comment_count == 2
    assert entry.publication_reference == "w20.06 12 par. 3"


@patch("daily_scripture.openai_extract._call_openai")
def test_not_found_raises(mock_call):
    mock_call.return_value = {"error": "not_found"}
    with pytest.raises(OpenAIExtractionError, match="could not find"):
        find_daily_entry_via_openai("https://x", date(2026, 7, 26), "sk-test")


@patch("daily_scripture.openai_extract._call_openai")
def test_missing_comments_raises(mock_call):
    mock_call.return_value = {
        "theme_scripture_citation": "Prov. 3:5",
        "theme_scripture_text": "Trust in Jehovah.",
        "comments": [],
    }
    with pytest.raises(OpenAIExtractionError, match="comment"):
        find_daily_entry_via_openai("https://x", date(2026, 7, 26), "sk-test")


@patch("daily_scripture.openai_extract._call_openai")
def test_missing_citation_raises(mock_call):
    mock_call.return_value = {
        "theme_scripture_citation": "",
        "theme_scripture_text": "Trust in Jehovah.",
        "comments": ["A comment."],
    }
    with pytest.raises(OpenAIExtractionError, match="citation"):
        find_daily_entry_via_openai("https://x", date(2026, 7, 26), "sk-test")


@patch("daily_scripture.openai_extract._call_openai", side_effect=RuntimeError("network down"))
def test_retries_exhausted_raises(mock_call, monkeypatch):
    monkeypatch.setattr("daily_scripture.openai_extract.BACKOFF_SECONDS", (0, 0))
    with pytest.raises(OpenAIExtractionError, match="failed after 3 attempts"):
        find_daily_entry_via_openai("https://x", date(2026, 7, 26), "sk-test")
    assert mock_call.call_count == 3
