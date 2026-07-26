"""Extract the daily text entry from the WOL source page HTML.

IMPORTANT — read this before touching selectors:
This automation was built in a sandboxed session with no network access to
wol.jw.org (outbound requests to that host were blocked by the environment's
network policy), so the selectors below could not be verified against a
live fetch. They target the structure WOL "daily text" pages have used
historically:

    <div id="article"> ... </div>
        <h1>...date heading...</h1>
        <p id="p1" class="themeScrp">   <!-- citation + scripture text -->
        <div id="p2"> <p>...</p> <p>...</p> ... </div>  <!-- comments -->
        <p class="sb">...publication reference...</p>

Because that structure can drift, `find_daily_entry` does NOT hard-fail if
those exact selectors miss — it falls back to heuristics (locate a heading
that parses as today's date, then walk forward through sibling paragraphs).
Run `daily-scripture test-extraction` from a machine with real network
access to wol.jw.org as the first setup step, and update the CSS selectors
in `SELECTORS` below if the live structure has changed. See README.md
"Extraction reliability & verifying selectors."
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from bs4 import BeautifulSoup, Tag

SELECTORS = {
    "article_container": "#article, .docSubContent, #content",
    "date_heading": "h1, h2.dateHeading, .todayDate",
    "theme_scripture": "#p1, .themeScrp",
    "comments_container": "#p2, .bodyTxt",
    "publication_ref": ".sb, .publication",
    "nav_noise": "nav, header, footer, .navHeader, .navFooter, .icon, script, style, .pageNum, .swiper-pagination",
}

# Matches headings like "Tuesday, July 28" or "July 28, 2026"
_MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|"
    "November|December"
)
_DATE_HEADING_RE = re.compile(
    rf"(?:(?P<weekday>[A-Za-z]+),\s*)?(?P<month>{_MONTHS})\s+(?P<day>\d{{1,2}})(?:,\s*(?P<year>\d{{4}}))?",
    re.IGNORECASE,
)


class ExtractionError(RuntimeError):
    """Raised when the daily entry cannot be reliably located or validated."""


@dataclass
class DailyEntry:
    entry_date: date
    date_heading_text: str
    theme_scripture_citation: str
    theme_scripture_text: str
    comments: list[str] = field(default_factory=list)
    publication_reference: str = ""

    @property
    def comment_count(self) -> int:
        return len(self.comments)


def _strip_noise(soup: BeautifulSoup) -> None:
    for el in soup.select(SELECTORS["nav_noise"]):
        el.decompose()


def _heading_matches_date(text: str, target: date) -> bool:
    match = _DATE_HEADING_RE.search(text)
    if not match:
        return False
    try:
        month = list(
            m for m in _MONTHS.split("|")
        ).index(match.group("month").capitalize()) + 1
    except ValueError:
        return False
    day = int(match.group("day"))
    year = int(match.group("year")) if match.group("year") else target.year
    return (month, day, year) == (target.month, target.day, target.year)


def _clean_paragraph_text(tag: Tag) -> str:
    text = tag.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _looks_like_nav_or_error_page(soup: BeautifulSoup) -> bool:
    text = soup.get_text(" ", strip=True).lower()
    if len(text) < 80:
        return True
    error_markers = ("page not found", "404", "sign in", "log in", "access denied")
    hits = sum(1 for marker in error_markers if marker in text)
    return hits >= 2


def find_daily_entry(html: str, target_date: date) -> DailyEntry:
    soup = BeautifulSoup(html, "lxml")

    _strip_noise(soup)

    if _looks_like_nav_or_error_page(soup):
        raise ExtractionError(
            "Fetched page looks like a navigation, error, or login page "
            "(too little text content or error markers present) — refusing "
            "to extract."
        )

    heading = None
    for candidate in soup.select(SELECTORS["date_heading"]):
        text = _clean_paragraph_text(candidate)
        if text and _heading_matches_date(text, target_date):
            heading = candidate
            break

    if heading is None:
        raise ExtractionError(
            f"No section heading matching today's date "
            f"({target_date.isoformat()}, America/Chicago) was found on the "
            "source page. The page structure may have changed, or today's "
            "entry is not yet published. Stopping before generating audio "
            "or sending anything."
        )

    date_heading_text = _clean_paragraph_text(heading)

    container = heading.find_parent(attrs={"id": "article"}) or heading.parent

    theme_el = None
    for sel in SELECTORS["theme_scripture"].split(", "):
        theme_el = (container.select_one(sel) if container else None) or soup.select_one(sel)
        if theme_el:
            break
    if theme_el is None:
        theme_el = heading.find_next("p")

    if theme_el is None:
        raise ExtractionError("Could not locate the theme scripture element.")

    theme_link = theme_el.find("a")
    citation = _clean_paragraph_text(theme_link) if theme_link else ""
    full_theme_text = _clean_paragraph_text(theme_el)
    if citation and full_theme_text.startswith(citation):
        scripture_text = full_theme_text[len(citation):].strip(" .—-")
    else:
        scripture_text = full_theme_text

    if not citation:
        raise ExtractionError("Theme scripture citation was not found.")
    if not scripture_text:
        raise ExtractionError("Theme scripture text was not found.")

    comments: list[str] = []
    comments_el = None
    for sel in SELECTORS["comments_container"].split(", "):
        comments_el = (container.select_one(sel) if container else None) or soup.select_one(sel)
        if comments_el:
            break

    publication_reference = ""
    if comments_el is not None:
        for p in comments_el.find_all("p"):
            text = _clean_paragraph_text(p)
            if not text:
                continue
            if p.get("class") and any("sb" in c or "publication" in c for c in p.get("class")):
                publication_reference = text
                continue
            comments.append(text)
    else:
        # Fallback: walk siblings after the theme scripture element.
        for sib in theme_el.find_all_next("p"):
            text = _clean_paragraph_text(sib)
            if not text:
                continue
            if sib.get("class") and any("sb" in c or "publication" in c for c in sib.get("class")):
                publication_reference = text
                break
            comments.append(text)

    if not comments:
        raise ExtractionError(
            "No comment/explanatory paragraphs were found for today's entry."
        )

    return DailyEntry(
        entry_date=target_date,
        date_heading_text=date_heading_text,
        theme_scripture_citation=citation,
        theme_scripture_text=scripture_text,
        comments=comments,
        publication_reference=publication_reference,
    )
