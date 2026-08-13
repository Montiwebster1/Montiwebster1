"""CLI entrypoint: daily-scripture run|preview|test-extraction|generate-audio|send-email|submit-journal."""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime, timezone

from . import clean_text, fetch, parse, state, tts, email_sender, journal, openai_extract
from .config import Config, ConfigError, load_config
from .dates import today_in_chicago
from .logging_setup import setup_logging

logger = logging.getLogger("daily_scripture.main")

EXIT_OK = 0
EXIT_PARTIAL = 2
EXIT_FAILURE = 1


def _resolve_date(args) -> date:
    if args.date:
        return date.fromisoformat(args.date)
    return today_in_chicago()


def _extract(cfg: Config, entry_date: date) -> parse.DailyEntry:
    """Direct HTTP fetch + HTML parse first (least brittle per spec). Only
    falls back to asking ChatGPT to browse the page when that fails AND
    EXTRACTION_FALLBACK=openai is configured — never silent, always logged.
    """
    try:
        html = fetch.fetch_page(cfg.source_url)
        entry = parse.find_daily_entry(html, entry_date)
    except (fetch.FetchError, parse.ExtractionError) as direct_exc:
        if (cfg.extraction.fallback_provider or "").lower().strip() != "openai":
            raise
        logger.warning(
            "Direct fetch/parse failed (%s); falling back to ChatGPT web-browsing extraction.",
            direct_exc,
        )
        entry = openai_extract.find_daily_entry_via_openai(
            cfg.source_url, entry_date, cfg.extraction.openai_api_key
        )
        logger.info("Extraction via OpenAI fallback succeeded for %s.", entry_date)

    logger.info(
        "Extraction OK: date=%s citation=%r comments=%d",
        entry.entry_date, entry.theme_scripture_citation, entry.comment_count,
    )
    return entry


def cmd_preview(args) -> int:
    cfg = load_config()
    entry_date = _resolve_date(args)
    setup_logging(cfg.logs_dir, entry_date)
    try:
        entry = _extract(cfg, entry_date)
    except (fetch.FetchError, parse.ExtractionError) as exc:
        print(f"Extraction failed: {exc}", file=sys.stderr)
        return EXIT_FAILURE

    journal_md = clean_text.build_journal_markdown(entry, cfg.source_url)
    print(journal_md)
    return EXIT_OK


def cmd_test_extraction(args) -> int:
    return cmd_preview(args)


def cmd_generate_audio(args) -> int:
    cfg = load_config(require_tts=True)
    entry_date = _resolve_date(args)
    setup_logging(cfg.logs_dir, entry_date)
    try:
        entry = _extract(cfg, entry_date)
    except (fetch.FetchError, parse.ExtractionError) as exc:
        print(f"Extraction failed: {exc}", file=sys.stderr)
        return EXIT_FAILURE

    cfg.audio_dir.mkdir(parents=True, exist_ok=True)
    script = clean_text.build_spoken_script(entry)
    out_path = cfg.audio_dir / f"daily-scripture-{entry_date.isoformat()}.mp3"
    try:
        result = tts.generate_audio(script, out_path, cfg)
    except tts.TTSError as exc:
        print(f"Audio generation failed: {exc}", file=sys.stderr)
        return EXIT_FAILURE

    print(f"Audio written to {result.path} (provider={result.provider}, format={result.format})")
    return EXIT_OK


def cmd_send_email(args) -> int:
    cfg = load_config(require_email=True)
    entry_date = _resolve_date(args)
    setup_logging(cfg.logs_dir, entry_date)
    run_state = state.load_state(cfg.state_dir, entry_date)
    if run_state is None or not run_state.audio_path:
        print("No existing audio found for this date; run `generate-audio` first.", file=sys.stderr)
        return EXIT_FAILURE
    if run_state.email_sent and not args.force_email:
        print(f"Email already sent for {entry_date} (message_id={run_state.email_message_id}). Use --force-email to resend.")
        return EXIT_OK

    try:
        entry = _extract(cfg, entry_date)
    except (fetch.FetchError, parse.ExtractionError) as exc:
        print(f"Extraction failed: {exc}", file=sys.stderr)
        return EXIT_FAILURE

    from pathlib import Path
    audio_path = Path(run_state.audio_path)
    subject = f"Daily Scripture — {clean_text.format_full_date(entry_date)}"
    body = clean_text.build_email_body(
        entry, cfg.source_url, journal_submitted=(run_state.journal_status == "submitted")
    )
    try:
        result = email_sender.send_daily_email(cfg, subject=subject, body=body, attachment_path=audio_path)
    except email_sender.EmailError as exc:
        print(f"Email send failed: {exc}", file=sys.stderr)
        return EXIT_FAILURE

    run_state.email_sent = True
    run_state.email_message_id = result.message_id
    state.mark_completed_now(run_state)
    state.save_state(cfg.state_dir, run_state)
    print(f"Email sent (provider={result.provider}, message_id={result.message_id})")
    return EXIT_OK


def cmd_submit_journal(args) -> int:
    cfg = load_config()
    entry_date = _resolve_date(args)
    setup_logging(cfg.logs_dir, entry_date)
    run_state = state.load_state(cfg.state_dir, entry_date) or state.RunState(date=entry_date.isoformat())
    if run_state.journal_status == "submitted" and not args.force_journal:
        print(f"Journal already submitted for {entry_date} (ref={run_state.journal_reference}). Use --force-journal to resubmit.")
        return EXIT_OK

    try:
        entry = _extract(cfg, entry_date)
    except (fetch.FetchError, parse.ExtractionError) as exc:
        print(f"Extraction failed: {exc}", file=sys.stderr)
        return EXIT_FAILURE

    journal_md = clean_text.build_journal_markdown(entry, cfg.source_url)
    result = journal.submit_journal_entry(cfg, entry_date, journal_md)
    run_state.journal_status = result.status
    run_state.journal_reference = result.reference
    state.save_state(cfg.state_dir, run_state)
    print(f"Journal status: {result.status} (ref={result.reference})")
    if result.reason:
        print(result.reason)
    return EXIT_OK if result.status != "failed" else EXIT_PARTIAL


def cmd_run(args) -> int:
    cfg = load_config(require_email=not args.dry_run, require_tts=not args.dry_run)
    entry_date = _resolve_date(args)
    log_path = setup_logging(cfg.logs_dir, entry_date)
    started_at = datetime.now(timezone.utc).isoformat()
    logger.info("Run started at %s for date=%s dry_run=%s", started_at, entry_date, args.dry_run)

    try:
        entry = _extract(cfg, entry_date)
    except (fetch.FetchError, parse.ExtractionError) as exc:
        logger.error("Extraction failed: %s", exc)
        print(f"Extraction failed, stopping before audio/email/journal: {exc}", file=sys.stderr)
        return EXIT_FAILURE

    journal_md = clean_text.build_journal_markdown(entry, cfg.source_url)
    script = clean_text.build_spoken_script(entry)
    new_hash = state.content_hash(journal_md)

    run_state = state.load_state(cfg.state_dir, entry_date) or state.RunState(date=entry_date.isoformat())
    content_changed = run_state.content_hash != new_hash
    run_state.content_hash = new_hash

    cfg.text_dir.mkdir(parents=True, exist_ok=True)
    (cfg.text_dir / f"daily-scripture-{entry_date.isoformat()}.md").write_text(journal_md, encoding="utf-8")

    # --- Audio ---
    cfg.audio_dir.mkdir(parents=True, exist_ok=True)
    audio_target = cfg.audio_dir / f"daily-scripture-{entry_date.isoformat()}.mp3"
    if run_state.audio_generated and not content_changed and not args.dry_run:
        from pathlib import Path
        audio_path = Path(run_state.audio_path)
        logger.info("Reusing existing audio at %s", audio_path)
    else:
        try:
            result = tts.generate_audio(script, audio_target, cfg)
        except tts.TTSError as exc:
            logger.error("Audio generation failed: %s", exc)
            print(f"Audio generation failed: {exc}", file=sys.stderr)
            return EXIT_FAILURE
        audio_path = result.path
        run_state.audio_generated = True
        run_state.audio_path = str(audio_path)
        logger.info("Audio generated: %s (provider=%s)", audio_path, result.provider)

    state.save_state(cfg.state_dir, run_state)

    if args.dry_run:
        logger.info("Dry run: skipping email send and journal submission.")
        print("DRY RUN complete. Extraction and audio generation succeeded.")
        print(f"  Text:  {cfg.text_dir / f'daily-scripture-{entry_date.isoformat()}.md'}")
        print(f"  Audio: {audio_path}")
        print(f"  Log:   {log_path}")
        return EXIT_OK

    # --- Email ---
    if run_state.email_sent and not args.force_email:
        logger.info("Email already sent for %s; skipping (no --force-email).", entry_date)
        email_status = "already_sent"
    else:
        subject = f"Daily Scripture — {clean_text.format_full_date(entry_date)}"
        journal_will_submit = True
        body = clean_text.build_email_body(entry, cfg.source_url, journal_submitted=journal_will_submit)
        try:
            result = email_sender.send_daily_email(cfg, subject=subject, body=body, attachment_path=audio_path)
        except email_sender.EmailError as exc:
            logger.error("Email send failed: %s", exc)
            run_state.completed_at = datetime.now(timezone.utc).isoformat()
            state.save_state(cfg.state_dir, run_state)
            print(f"Email send failed: {exc}", file=sys.stderr)
            return EXIT_FAILURE
        run_state.email_sent = True
        run_state.email_message_id = result.message_id
        state.save_state(cfg.state_dir, run_state)
        email_status = "sent"
        logger.info("Email sent: provider=%s message_id=%s", result.provider, result.message_id)

    # --- Journal ---
    if run_state.journal_status == "submitted" and not args.force_journal:
        logger.info("Journal already submitted for %s; skipping (no --force-journal).", entry_date)
    else:
        result = journal.submit_journal_entry(cfg, entry_date, journal_md)
        run_state.journal_status = result.status
        run_state.journal_reference = result.reference
        if result.reason:
            logger.info("Journal handoff note: %s", result.reason)

    state.mark_completed_now(run_state)
    state.save_state(cfg.state_dir, run_state)

    if run_state.journal_status == "submitted":
        print(f"Complete success. Email {email_status}, journal submitted (ref={run_state.journal_reference}).")
        return EXIT_OK
    if run_state.journal_status == "pending":
        print(
            f"Partial success: email {email_status} "
            f"(message_id={run_state.email_message_id}), journal handoff PENDING "
            f"— {run_state.journal_reference}"
        )
        return EXIT_PARTIAL
    print(f"Partial success: email {email_status}, journal submission FAILED.", file=sys.stderr)
    return EXIT_PARTIAL


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="daily-scripture")
    sub = p.add_subparsers(dest="command", required=True)

    def add_common(sp):
        sp.add_argument("--date", help="Explicit date YYYY-MM-DD (testing only)")

    run_p = sub.add_parser("run", help="Run the complete workflow")
    add_common(run_p)
    run_p.add_argument("--dry-run", action="store_true", help="Skip email + journal submission")
    run_p.add_argument("--force-email", action="store_true")
    run_p.add_argument("--force-journal", action="store_true")
    run_p.set_defaults(func=cmd_run)

    preview_p = sub.add_parser("preview", help="Preview extracted content only")
    add_common(preview_p)
    preview_p.set_defaults(func=cmd_preview)

    test_p = sub.add_parser("test-extraction", help="Test extraction only")
    add_common(test_p)
    test_p.set_defaults(func=cmd_test_extraction)

    audio_p = sub.add_parser("generate-audio", help="Generate audio without sending")
    add_common(audio_p)
    audio_p.set_defaults(func=cmd_generate_audio)

    email_p = sub.add_parser("send-email", help="Retry only email")
    add_common(email_p)
    email_p.add_argument("--force-email", action="store_true")
    email_p.set_defaults(func=cmd_send_email)

    journal_p = sub.add_parser("submit-journal", help="Retry only journal submission")
    add_common(journal_p)
    journal_p.add_argument("--force-journal", action="store_true")
    journal_p.set_defaults(func=cmd_submit_journal)

    return p


def cli(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "force_email"):
        args.force_email = False
    if not hasattr(args, "force_journal"):
        args.force_journal = False
    if not hasattr(args, "dry_run"):
        args.dry_run = False
    try:
        return args.func(args)
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_FAILURE


if __name__ == "__main__":
    sys.exit(cli())
