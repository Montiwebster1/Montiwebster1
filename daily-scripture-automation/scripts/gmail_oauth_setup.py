"""One-time helper: exchange a Google OAuth client (Desktop app type) for a
Gmail refresh token, so the automation can send email without ever storing
a password.

Usage (run on the machine that will actually run the scheduled job, not in
a throwaway sandbox — the printed refresh token is a long-lived secret):

    python scripts/gmail_oauth_setup.py

It opens a browser, asks you to sign in and approve "Send email on your
behalf" (gmail.send scope only — this script never reads your mail), then
prints the three values to put in .env:

    GMAIL_CLIENT_ID=...
    GMAIL_CLIENT_SECRET=...
    GMAIL_REFRESH_TOKEN=...

Requires: pip install -e ".[gmail]" google-auth-oauthlib
"""
from __future__ import annotations

import sys

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def main() -> int:
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print(
            "Missing dependency. Run:\n"
            "  pip install google-auth-oauthlib\n",
            file=sys.stderr,
        )
        return 1

    print(
        "Paste the Client ID and Client Secret from Google Cloud Console\n"
        "(APIs & Services > Credentials > your Desktop app OAuth client).\n"
    )
    client_id = input("Client ID: ").strip()
    client_secret = input("Client Secret: ").strip()

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    print("\nOpening a browser to sign in and approve access...\n")
    creds = flow.run_local_server(port=0)

    if not creds.refresh_token:
        print(
            "\nNo refresh token was returned. This usually means you've "
            "already authorized this app before. Go to "
            "https://myaccount.google.com/permissions, remove access for "
            "this app, and run this script again so Google issues a fresh "
            "refresh token.",
            file=sys.stderr,
        )
        return 1

    print("\nSuccess. Add these to your .env file:\n")
    print(f"EMAIL_PROVIDER=gmail_oauth")
    print(f"GMAIL_CLIENT_ID={client_id}")
    print(f"GMAIL_CLIENT_SECRET={client_secret}")
    print(f"GMAIL_REFRESH_TOKEN={creds.refresh_token}")
    print(
        "\nThe refresh token above is a long-lived secret — treat it like a "
        "password. Do not paste it anywhere except your local .env file."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
