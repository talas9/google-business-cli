import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

# Load .env from CLI directory, then project root (if different)
_cli_dir = Path(__file__).resolve().parent.parent
if load_dotenv is not None:
    load_dotenv(_cli_dir / ".env")

PROJECT_ROOT = Path(os.environ.get("GADS_PROJECT_ROOT", _cli_dir.parent))

if load_dotenv is not None and (PROJECT_ROOT / ".env").exists():
    load_dotenv(PROJECT_ROOT / ".env", override=False)

# ── Paths (all overridable) ──────────────────────────────────
DB_PATH = Path(os.environ.get("GADS_DB_PATH", PROJECT_ROOT / "data" / "gads.db"))
CREDS_PATH = Path(os.environ.get("GADS_CREDENTIALS_PATH", PROJECT_ROOT / "credentials" / "google-ads-oauth.json"))
SNAPSHOTS_DIR = Path(os.environ.get("GADS_SNAPSHOTS_DIR", PROJECT_ROOT / "snapshots"))

# ── Google Ads ───────────────────────────────────────────────
DEV_TOKEN = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN", "")
LOGIN_CUSTOMER_ID = os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "")
CUSTOMER_ID = os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "")
API_VERSION = os.environ.get("GOOGLE_ADS_API_VERSION", "v18")

# ── Google Merchant Center ───────────────────────────────────
MERCHANT_CENTER_ID = os.environ.get("GOOGLE_MERCHANT_CENTER_ID", "")

# ── Google Analytics / GA4 ───────────────────────────────────
GA4_PROPERTY_ID = os.environ.get("GOOGLE_GA4_PROPERTY_ID", "")

# ── Timezone (IANA format, e.g. "Asia/Dubai", "America/New_York") ──
TZ_NAME = os.environ.get("GADS_TIMEZONE", "UTC")
