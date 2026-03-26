import json

import click
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from .config import CREDS_PATH


def get_credentials():
    """Load and refresh OAuth credentials."""
    if not CREDS_PATH.exists():
        click.secho(f"✗ Credentials not found: {CREDS_PATH}", fg="red", err=True)
        raise SystemExit(1)

    with open(CREDS_PATH) as f:
        creds_data = json.load(f)

    creds = Credentials.from_authorized_user_info(creds_data)
    if creds.expired:
        creds.refresh(Request())
        with open(CREDS_PATH, "w") as f:
            f.write(creds.to_json())
    return creds
