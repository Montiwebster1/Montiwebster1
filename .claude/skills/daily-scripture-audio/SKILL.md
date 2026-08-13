---
name: daily-scripture-audio
description: Maintains, verifies, and troubleshoots Monti's Daily Scripture-to-Audio and Journal Automation (fetches wol.jw.org daily text, narrates it to MP3, emails it, hands it off to the "Journal - My Children" ChatGPT project). Use whenever Monti mentions "daily scripture," "scripture audio," "daily text automation," the "Journal - My Children" handoff, or asks to build/fix/extend this automation — even if worded differently. Do NOT rebuild this from scratch; the working implementation already lives in daily-scripture-automation/ at the repo root.
---

# Daily Scripture-to-Audio and Journal Automation

This automation already exists at `daily-scripture-automation/` in this
repo, on the `main`/default line of work (merged from the most complete of
five prior rebuild attempts). **Before writing any new code for this task,
read `daily-scripture-automation/README.md` and the existing
`src/daily_scripture/` modules.** Extend or fix what's there — do not start
a parallel implementation. Five earlier sessions each rebuilt this from
scratch on throwaway branches because nothing was merged; that's the
mistake this skill exists to stop.

## What it does

Every morning at 5:00 AM America/Chicago:
1. Fetches the daily text from `SOURCE_URL` (wol.jw.org daily text page).
2. Locates today's date section, extracts date + scripture citation +
   scripture text + comments — verbatim, never summarized.
3. Narrates it to audio (MP3 via cloud TTS, or WAV via the offline
   `pyttsx3`/`espeak-ng` fallback).
4. Emails the audio to `RECIPIENT_EMAIL`.
5. Hands the same content off to the ChatGPT project "Journal - My
   Children" (queued to `output/journal-handoff/` by default until an
   authenticated integration is configured — see README's "Journal
   handoff" section).

Full architecture, CLI commands, scheduling instructions (systemd/cron/
launchd/Task Scheduler), and troubleshooting are documented in
`daily-scripture-automation/README.md` — treat that file as the source of
truth, not this skill.

## Known open item (check first)

The extraction selectors in `src/daily_scripture/parse.py` were written
from the page's known historical structure but **have never been verified
against a live fetch** — every prior build session's sandbox blocked
outbound access to `wol.jw.org`. If you have live network access in this
session:

```bash
cd daily-scripture-automation
pip install -e ".[dev]"
daily-scripture test-extraction
```

If the output is wrong (missing citation, wrong paragraphs, wrong date
match), fix the CSS selectors in `parse.py`'s `SELECTORS` dict against the
live HTML — do not rewrite the surrounding fetch/parse/clean pipeline,
it's already built and tested (44 passing tests in `tests/`, all against
saved HTML fixtures).

## Working on this task

1. `cd daily-scripture-automation && pytest tests/ -q` — confirm the 44
   existing tests still pass before and after any change.
2. Check `.env.example` for every configurable value (source URL,
   recipient, TTS provider, email provider, journal handoff method) —
   nothing is hard-coded, so a new requirement is usually a new env var,
   not new plumbing.
3. Gmail OAuth, TTS provider keys, and the ChatGPT browser handoff profile
   all require secrets Monti holds, not something this skill or a sandbox
   session can supply — if a task needs one of those, say so and ask
   Monti to run the relevant setup step from the README on his own
   machine (e.g. `scripts/gmail_oauth_setup.py`) rather than blocking
   silently or inventing a workaround.
4. If asked to schedule/deploy it, point to the README's "Scheduling"
   section (systemd timer preferred on Linux, launchd on macOS, Task
   Scheduler on Windows) rather than writing a new scheduler mechanism.
5. When the change is done, commit it in `daily-scripture-automation/`
   alongside a test that covers it — this project's convention is fixture
   -based tests with no live network calls (see `tests/fixtures/`).
