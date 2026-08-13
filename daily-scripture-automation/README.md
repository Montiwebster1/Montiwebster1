# Daily Scripture-to-Audio and Journal Automation

Every morning at 5:00 AM America/Chicago, this automation:

1. Fetches the daily text from `https://wol.jw.org/en/wol/d/r1/lp-e/1102026216`.
2. Locates the section matching today's date (America/Chicago).
3. Extracts the date, theme scripture citation, scripture text, and all
   comment paragraphs — wording preserved exactly, no summarizing.
4. Narrates it to an MP3 (or WAV fallback — see "Audio format" below).
5. Emails the audio to `montiwebster@gmail.com`.
6. Submits the same content, in a fixed template, into a new session of the
   ChatGPT project **"Journal - My Children"** — or, if no authenticated
   integration is configured, saves it to a handoff queue and says so
   honestly in the email and the run log (see "Journal handoff" below).

## ⚠️ Known limitation from this build session

This automation was built and tested in a sandboxed session whose network
policy **blocks outbound requests to `wol.jw.org`** (confirmed via a direct
`403`/`connect_rejected` from the environment's proxy). That means:

- The extraction selectors in `src/daily_scripture/parse.py` were written
  from the WOL "daily text" page's known historical structure, **not
  verified against a live fetch**.
- The one required live extraction test (see Acceptance Criteria) could not
  be run here.

**Before relying on this in production**, run this from a machine/session
with real network access to wol.jw.org:

```bash
daily-scripture test-extraction
```

If the output looks wrong (missing citation, wrong paragraphs, etc.), open
the page's HTML in a browser, compare against `SELECTORS` in `parse.py`,
and adjust the CSS selectors there. Everything else (cleaning, audio,
email, journal handoff, state, tests) was fully built and tested in this
session using a saved HTML fixture and does not depend on live network
access.

### ChatGPT extraction fallback

Direct HTTP fetch + HTML parsing is always tried first — it's the least
brittle method and the spec's preferred approach. If it fails (site
structure changed, transient block, etc.) and `EXTRACTION_FALLBACK=openai`
is set with an `OPENAI_API_KEY`, the automation asks ChatGPT (OpenAI
Responses API with the `web_search` tool) to browse the same page, locate
the matching date, and return the same fields under the same "verbatim, no
summarizing" instruction — see `src/daily_scripture/openai_extract.py`.
This is a fallback, not a replacement: if `EXTRACTION_FALLBACK` is unset,
a direct-fetch failure still stops the run cleanly, as required.

Outbound requests to `api.openai.com` were also blocked in this sandboxed
build session, so this fallback path is implemented and unit-tested against
a mocked OpenAI client (`tests/test_openai_extract.py`) but has not been
exercised against the real API. Verify it the same way as the primary
path — `daily-scripture test-extraction` with `EXTRACTION_FALLBACK=openai`
set and the primary selectors temporarily broken (or just watch the log
for "falling back to ChatGPT web-browsing extraction").

## Install

```bash
cd daily-scripture-automation
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# edit .env with real values (see Configuration below)
```

Install extras only for the providers you'll actually use:

```bash
pip install -e ".[gmail]"           # Gmail OAuth email delivery
pip install -e ".[openai-tts]"      # OpenAI TTS provider
pip install -e ".[browser-handoff]" # Playwright-based journal handoff
```

The local TTS fallback needs the `espeak-ng` system package:

```bash
# Debian/Ubuntu
sudo apt-get install -y espeak-ng
# macOS
brew install espeak-ng   # optional — macOS also has `say`, but pyttsx3 uses espeak's nsss driver natively on macOS, no install needed
```

## Configuration

All configuration is environment variables, loaded from `.env` (never
committed — see `.gitignore`). See `.env.example` for the full list with
comments. Nothing is hard-coded: not the recipient, not any API key, not
any OAuth secret.

### Email (pick one)

- **Gmail OAuth** (preferred — what this deployment uses): see
  "Gmail OAuth setup" below for the full step-by-step.
- **SMTP**: set `EMAIL_PROVIDER=smtp` plus `SMTP_HOST`, `SMTP_PORT`,
  `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_FROM`. For Gmail SMTP, use an
  [App Password](https://myaccount.google.com/apppasswords), not your
  normal password.

#### Gmail OAuth setup

Run this on the machine that will actually run the 5 AM job — not a
throwaway sandbox, since step 4 prints a long-lived secret.

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → create
   a project (or pick an existing one) → **APIs & Services → Library** →
   enable the **Gmail API**.
2. **APIs & Services → OAuth consent screen** → choose **External** (unless
   you have a Workspace org) → fill in the required app name/support email
   → add your own Gmail address as a **Test user** (this keeps the app in
   "Testing" mode, which is fine for personal use and doesn't require
   Google review).
3. **APIs & Services → Credentials → Create Credentials → OAuth client ID**
   → Application type **Desktop app** → note the **Client ID** and
   **Client Secret** it generates.
4. Install the OAuth helper dependency and run the included script:
   ```bash
   pip install -e ".[gmail]"
   python scripts/gmail_oauth_setup.py
   ```
   It asks for the Client ID/Secret from step 3, opens a browser for you to
   sign in and approve "Send email on your behalf" (only the `gmail.send`
   scope is requested — this never reads your mail), then prints the
   `GMAIL_CLIENT_ID` / `GMAIL_CLIENT_SECRET` / `GMAIL_REFRESH_TOKEN` lines
   to paste into `.env`, plus `EMAIL_PROVIDER=gmail_oauth`.
5. Verify with a real send:
   ```bash
   daily-scripture run --date 2026-07-26 --dry-run   # confirms extraction+audio first
   daily-scripture send-email --date 2026-07-26      # actually sends, needs prior audio from a non-dry run
   ```
   `send-email` only succeeds and reports a message ID once Gmail actually
   confirms the send — it won't print success on a token/auth failure.

If step 4 prints "No refresh token was returned," you've likely authorized
this app before — revoke it at
[myaccount.google.com/permissions](https://myaccount.google.com/permissions)
and re-run the script so Google issues a fresh one.

### Text-to-speech (pick one, in priority order)

1. Leave `TTS_PROVIDER` unset (or `local`) → uses the offline `pyttsx3` +
   `espeak-ng` engine. No key needed. Produces **WAV**, not MP3, because
   pyttsx3 cannot encode MP3 directly — this is the documented fallback
   format the spec permits when MP3 isn't available.
2. `TTS_PROVIDER=elevenlabs` + `TTS_API_KEY` (+ optional `TTS_VOICE_ID`) →
   produces MP3.
3. `TTS_PROVIDER=openai` + `TTS_API_KEY` (+ optional `TTS_VOICE_ID`, default
   `alloy`) → produces MP3.

Amazon Polly / Google Cloud TTS / Azure Speech are next in the spec's
priority order but are not wired into `tts.py` in this build (no accounts
were available to implement/test against). Adding one is a single function
in `tts.py` following the `_generate_elevenlabs` / `_generate_openai`
pattern — plug it into `_PROVIDERS` and document its env vars.

### Journal handoff ("Journal - My Children")

Set `CHATGPT_HANDOFF_METHOD`:

- `queue` (default, and what this build actually uses): no official OpenAI/
  ChatGPT API exists today for "create a session inside a named project."
  This method writes the structured entry to
  `output/journal-handoff/YYYY-MM-DD.md`, marks the run's journal status as
  `pending`, and adjusts the email wording to say submission requires an
  authenticated ChatGPT integration. **Nothing is ever faked as
  "submitted" unless it actually was.**
- `browser`: authenticated Playwright automation against an *already
  logged-in* persistent Chrome profile. Requires
  `CHATGPT_BROWSER_PROFILE_PATH` pointing at that profile directory. Will
  never attempt to enter a password, OTP, or bypass a CAPTCHA/MFA
  challenge — if the profile isn't already authenticated, it fails and
  falls back to `queue`.
- `api`: reserved for if/when an official project-session API exists.
  Currently always falls back to `queue`.

## Command-line interface

```bash
daily-scripture run                              # full workflow for today
daily-scripture run --dry-run                    # extract + generate audio only, no email/journal
daily-scripture run --date 2026-07-26 --dry-run  # test a specific date
daily-scripture run --force-email                # resend even if already sent today
daily-scripture run --force-journal              # resubmit even if already submitted today
daily-scripture preview                          # print extracted content, no side effects
daily-scripture test-extraction                  # same as preview — verify the scraper
daily-scripture generate-audio                   # extraction + TTS only
daily-scripture send-email                       # retry only the email step (reuses existing audio)
daily-scripture submit-journal                   # retry only the journal step
```

Exit codes: `0` complete success · `2` partial success (e.g. email sent,
journal handoff pending/failed) · `1` complete failure.

## Scheduling (5:00 AM America/Chicago, DST-safe)

### Linux — systemd timer (preferred)

```bash
# Install
mkdir -p ~/.config/systemd/user
cp scheduler/daily-scripture.service scheduler/daily-scripture.timer ~/.config/systemd/user/
systemctl --user daemon-reload

# Enable
systemctl --user enable --now daily-scripture.timer

# Disable
systemctl --user disable --now daily-scripture.timer

# Manual test
systemctl --user start daily-scripture.service

# Status
systemctl --user status daily-scripture.timer
systemctl --user list-timers daily-scripture.timer
```

`OnCalendar=*-*-* 05:00:00 America/Chicago` in the `.timer` unit encodes the
timezone explicitly, so it fires at 5:00 AM Central regardless of the host
machine's own timezone setting, and correctly follows the CST/CDT
transition (verified by unit test — see `tests/test_dates.py`).

### Linux — cron fallback

Use `scheduler/crontab.txt` (`CRON_TZ=America/Chicago` on Vixie
cron/cronie) if systemd user timers aren't available:

```bash
crontab -e   # paste the contents of scheduler/crontab.txt, editing the path
```

### macOS — launchd

```bash
cp scheduler/com.montiwebster.dailyscripture.plist ~/Library/LaunchAgents/
# edit REPLACE_ME paths inside the plist first
launchctl load ~/Library/LaunchAgents/com.montiwebster.dailyscripture.plist   # enable
launchctl unload ~/Library/LaunchAgents/com.montiwebster.dailyscripture.plist # disable
launchctl start com.montiwebster.dailyscripture                              # manual test
launchctl list | grep dailyscripture                                         # status
```

launchd's `StartCalendarInterval` fires by the **machine's local system
timezone**, not a named zone — confirm the Mac's own timezone is set to
Central Time (System Settings → General → Date & Time) or the 5:00 AM
firing will drift.

### Windows — Task Scheduler

See `scheduler/windows_task_scheduler.md` for install/enable/disable/test/
status PowerShell commands.

### Log location (all platforms)

`logs/daily-scripture-YYYY-MM-DD.log` — one structured log file per run
date, secrets automatically redacted (see Privacy below).

## Idempotency & state

Each date's run produces `state/YYYY-MM-DD.json`:

```json
{
  "date": "2026-07-26",
  "content_hash": "...",
  "audio_generated": true,
  "audio_path": "output/audio/daily-scripture-2026-07-26.mp3",
  "email_sent": true,
  "email_message_id": "...",
  "journal_status": "pending",
  "journal_reference": "output/journal-handoff/2026-07-26.md",
  "completed_at": "2026-07-26T10:05:00+00:00"
}
```

Re-running `daily-scripture run` for a date that's already complete is a
no-op for email/journal unless `--force-email` / `--force-journal` is
passed. If audio succeeded but email failed, a retry reuses the existing
audio file instead of regenerating it. Content changes are detected via a
SHA-256 hash of the structured journal text.

## Testing

```bash
pytest tests/ -v
```

38 tests, all using a saved HTML fixture (`tests/fixtures/sample_page.html`
+ 3 edge-case fixtures) — no live requests. Covers: date selection near
midnight Central Time, DST spring-forward/fall-back boundaries, missing
date entry, missing scripture text, missing comments, unexpected HTML
structure changes, text cleaning, spoken-script structure, journal template
formatting, duplicate-run prevention, partial-failure recovery, email
attachment construction, journal handoff fallback, and secret redaction.

## Privacy — what's never logged

Passwords, OAuth access/refresh tokens, API keys, session cookies, and
authorization headers are redacted automatically by
`logging_setup.RedactingFilter` before anything is written to disk. Full
ChatGPT responses are never logged, only status + reference (e.g. a
conversation URL or the handoff-queue file path).

## Architecture

```
src/daily_scripture/
  config.py         — env loading + strict validation
  fetch.py           — HTTP fetch, 3 retries w/ backoff, no-retry on 401/403/404
  parse.py            — HTML extraction, date matching, structural validation
  dates.py            — DST-safe America/Chicago date resolution
  clean_text.py       — spoken-script + journal-markdown + email-body builders
  tts.py               — pluggable TTS providers (elevenlabs/openai/local)
  email_sender.py      — gmail_oauth / smtp delivery
  journal.py            — api / browser / queue handoff to "Journal - My Children"
  state.py               — idempotent run-state JSON records
  logging_setup.py        — structured per-date logs + secret redaction
  main.py                  — CLI (run/preview/test-extraction/generate-audio/send-email/submit-journal)
```

## Troubleshooting

- **"No section heading matching today's date"** — the page structure has
  likely changed, or today's entry isn't published yet. Selectors live in
  `parse.py`'s `SELECTORS` dict.
- **SMTP auth failure** — for Gmail, confirm you're using an App Password,
  not your account password (App Passwords require 2FA enabled).
- **`espeak not installed`** — install `espeak-ng` (see Install).
- **Journal status stuck on `pending`** — expected until an authenticated
  ChatGPT integration (`browser` or a future `api`) is configured. The
  entry is sitting in `output/journal-handoff/YYYY-MM-DD.md` for manual
  submission in the meantime.

## Setting up the ChatGPT project handoff (when ready)

1. Obtain a Chrome/Chromium profile already logged into chatgpt.com with
   the "Journal - My Children" project visible.
2. Set `CHATGPT_HANDOFF_METHOD=browser` and
   `CHATGPT_BROWSER_PROFILE_PATH=/path/to/that/profile` in `.env`.
3. Install Playwright's browser: `playwright install chromium` (one-time).
4. Run `daily-scripture submit-journal --date <a-past-date-already-run>` to
   test without re-sending email.
