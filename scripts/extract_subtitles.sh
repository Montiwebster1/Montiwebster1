#!/usr/bin/env bash
#
# Download subtitles (manual + auto-generated) for a YouTube video via yt-dlp,
# without downloading the video itself.
#
# Usage:
#   scripts/extract_subtitles.sh <youtube-url> [output-dir] [sub-langs]
#
# Examples:
#   scripts/extract_subtitles.sh "https://www.youtube.com/watch?v=XXXXXXXXXXX"
#   scripts/extract_subtitles.sh "https://youtu.be/XXXXXXXXXXX" ./subs "en.*"

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <youtube-url> [output-dir] [sub-langs]" >&2
  exit 1
fi

URL="$1"
OUTPUT_DIR="${2:-./subtitles}"
SUB_LANGS="${3:-en.*}"

if ! command -v yt-dlp >/dev/null 2>&1; then
  echo "Error: yt-dlp is not installed or not on PATH." >&2
  echo "Install it with: pip install -U yt-dlp" >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

yt-dlp \
  --skip-download \
  --write-subs \
  --write-auto-subs \
  --sub-langs "$SUB_LANGS" \
  --sub-format "vtt" \
  --output "$OUTPUT_DIR/%(title)s.%(ext)s" \
  "$URL"
