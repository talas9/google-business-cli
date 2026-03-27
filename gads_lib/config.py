"""Configuration for google-business-cli.

Scope detection (determines where credentials, data, and .env live):
  1. GADS_PROJECT_ROOT env var set       → project scope (that directory)
  2. CWD has data/, credentials/, or .env → project scope (CWD)
  3. Otherwise                            → global scope (~/.config/gads/)

Within any scope, .env is loaded and all paths resolve relative to the scope root.
Environment variables always override detected paths.
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

# ── Scope detection ──────────────────────────────────────────
GLOBAL_HOME = Path.home() / ".config" / "gads"


def _detect_scope():
    """Determine scope root and whether we're global or project-local."""
    explicit = os.environ.get("GADS_PROJECT_ROOT")
    if explicit:
        return Path(explicit), "project"

    cwd = Path.cwd()
    if (cwd / "data").is_dir() or (cwd / "credentials").is_dir() or (cwd / ".env").exists():
        return cwd, "project"

    # Check if we're inside a submodule layout (google-business-cli/ inside a project)
    pkg_dir = Path(__file__).resolve().parent.parent  # google-business-cli/
    parent = pkg_dir.parent
    if (parent / "data").is_dir() or (parent / "credentials").is_dir():
        return parent, "project"

    return GLOBAL_HOME, "global"


SCOPE_ROOT, SCOPE_TYPE = _detect_scope()

# ── Load .env ────────────────────────────────────────────────
if load_dotenv is not None:
    # Load scope-specific .env first (highest priority)
    load_dotenv(SCOPE_ROOT / ".env")
    # If project scope, also check global as fallback for shared secrets
    if SCOPE_TYPE == "project":
        load_dotenv(GLOBAL_HOME / ".env", override=False)

# ── Paths (all overridable, default to scope root) ───────────
PROJECT_ROOT = SCOPE_ROOT  # alias for backward compat
CONFIG_HOME = GLOBAL_HOME

DB_PATH = Path(os.environ.get("GADS_DB_PATH", SCOPE_ROOT / "data" / "gads.db"))
CREDS_PATH = Path(os.environ.get("GADS_CREDENTIALS_PATH", SCOPE_ROOT / "credentials" / "google-ads-oauth.json"))
SNAPSHOTS_DIR = Path(os.environ.get("GADS_SNAPSHOTS_DIR", SCOPE_ROOT / "snapshots"))

# ── Google Ads ───────────────────────────────────────────────
DEV_TOKEN = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN", "")
LOGIN_CUSTOMER_ID = os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "")
CUSTOMER_ID = os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "")
API_VERSION = os.environ.get("GOOGLE_ADS_API_VERSION", "v19")

# ── Google Merchant Center ───────────────────────────────────
MERCHANT_CENTER_ID = os.environ.get("GOOGLE_MERCHANT_CENTER_ID", "")

# ── Google Analytics / GA4 ───────────────────────────────────
GA4_PROPERTY_ID = os.environ.get("GOOGLE_GA4_PROPERTY_ID", "")

# ── Timezone (IANA format, e.g. "Asia/Dubai", "America/New_York") ──
TZ_NAME = os.environ.get("GADS_TIMEZONE", "UTC")

# ── Currency (ISO 4217 code, e.g. "USD", "AED", "EUR") ──────
CURRENCY = os.environ.get("GADS_CURRENCY", "USD")
