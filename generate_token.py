"""Generate OAuth token for Google platform API access.

Creates credentials with scopes for Google Ads, Business Profile,
Merchant Center, and Google Analytics.

Requires client_secret.json from Google Cloud Console:
  https://console.cloud.google.com/apis/credentials

Usage:
    python generate_token.py
    python generate_token.py --port 9090
"""
import argparse
import os
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

PROJECT_ROOT = Path(os.environ.get("GADS_PROJECT_ROOT", Path(__file__).resolve().parent.parent))
CREDENTIALS_DIR = Path(os.environ.get("GADS_CREDENTIALS_DIR", PROJECT_ROOT / "credentials"))

SCOPES = [
    "https://www.googleapis.com/auth/adwords",
    "https://www.googleapis.com/auth/business.manage",
    "https://www.googleapis.com/auth/content",
    "https://www.googleapis.com/auth/analytics.readonly",
]

CLIENT_SECRET = CREDENTIALS_DIR / "client_secret.json"
TOKEN_OUTPUT = CREDENTIALS_DIR / "google-ads-oauth.json"


def main():
    parser = argparse.ArgumentParser(description="Generate OAuth token for Google APIs")
    parser.add_argument("--port", type=int, default=9090, help="Local server port for OAuth callback")
    args = parser.parse_args()

    if not CLIENT_SECRET.exists():
        print(f"ERROR: client_secret.json not found at {CLIENT_SECRET}")
        print("Download it from https://console.cloud.google.com/apis/credentials")
        print(f"Save it to: {CLIENT_SECRET}")
        raise SystemExit(1)

    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
    creds = flow.run_local_server(port=args.port)

    with open(TOKEN_OUTPUT, "w") as f:
        f.write(creds.to_json())

    print(f"✓ Token saved to {TOKEN_OUTPUT}")
    print(f"  Scopes: {', '.join(SCOPES)}")


if __name__ == "__main__":
    main()
