"""gads — Unified Google platform CLI.

Manage Google Ads, Google Business Profile, Google Merchant Center,
and Google Analytics (GA4) from a single CLI. Designed for use with
Claude Code and AI coding agents.

All configuration is via environment variables / .env file.
See .env.example for the full list.
"""

import os
import subprocess
import sys
from datetime import datetime, timedelta

import click

from gads_lib import (
    CONFIG_HOME,
    CREDS_PATH,
    CURRENCY,
    CUSTOMER_ID,
    DB_PATH,
    DEV_TOKEN,
    GA4_PROPERTY_ID,
    GLOBAL_HOME,
    LOGIN_CUSTOMER_ID,
    MERCHANT_CENTER_ID,
    PROJECT_ROOT,
    SCOPE_ROOT,
    SCOPE_TYPE,
    SNAPSHOTS_DIR,
    TZ_NAME,
    ads_mutate,
    ads_batch_mutate,
    ads_upload_click_conversions,
    flatten,
    ga4_get_metadata,
    ga4_run_realtime_report,
    ga4_run_report,
    gbp_delete_reply,
    gbp_get_location,
    gbp_list_accounts,
    gbp_list_locations,
    gbp_list_reviews,
    gbp_reply_review,
    generate_keyword_ideas,
    generate_keyword_forecast,
    get_credentials,
    get_db,
    mc_get_account,
    mc_get_account_status,
    mc_get_return_policy,
    mc_get_shipping,
    mc_list_datafeeds,
    mc_list_product_statuses,
    mc_list_products,
    now_local,
    print_json,
    print_table,
    run_gaql,
    today_local,
)


from gads_lib import __version__


@click.group()
@click.version_option(__version__, prog_name="gads")
def cli():
    """gads — Unified Google platform CLI."""
    pass


@cli.group()
def auth():
    """Authentication and credential diagnostics."""
    pass


@cli.group()
def ads():
    """Google Ads commands."""
    pass


@cli.group()
def gbp():
    """Google Business Profile commands."""
    pass


@cli.group()
def merchant():
    """Google Merchant Center commands."""
    pass


@cli.group()
def ga4():
    """Google Analytics / GA4 commands."""
    pass


def enforce_allowed_caller():
    """Optional caller enforcement for agent delegation models."""
    if os.environ.get("GADS_ENFORCE_CALLER") != "1":
        return
    expected = os.environ.get("GADS_EXPECTED_CALLER", "google-platform-operator")
    caller = os.environ.get("GADS_CALLER_AGENT", "")
    if caller != expected:
        click.secho(
            f"✗ gads is restricted to the '{expected}' agent when GADS_ENFORCE_CALLER=1",
            fg="red", err=True,
        )
        raise SystemExit(1)


# ── Top-level commands ───────────────────────────────────────


@auth.command("status")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def auth_status(as_json):
    """Show current credential and env status (never prints secrets)."""
    scopes = []
    creds_present = CREDS_PATH.exists()
    if creds_present:
        creds = get_credentials()
        scopes = sorted(list(creds.scopes or []))

    payload = {
        "scope": SCOPE_TYPE,
        "scope_root": str(SCOPE_ROOT),
        "credentials_present": creds_present,
        "developer_token_present": bool(DEV_TOKEN),
        "login_customer_id_set": bool(LOGIN_CUSTOMER_ID),
        "customer_id_set": bool(CUSTOMER_ID),
        "merchant_center_id_set": bool(MERCHANT_CENTER_ID),
        "ga4_property_id_set": bool(GA4_PROPERTY_ID),
        "timezone": TZ_NAME,
        "currency": CURRENCY,
        "scopes": scopes,
        "db_path": str(DB_PATH),
        "db_present": DB_PATH.exists(),
    }

    if as_json:
        print_json(payload)
        return

    click.secho("\n  Auth Status\n", fg="white", bold=True)
    rows = [{"field": k, "value": str(v)} for k, v in payload.items()]
    print_table(rows, ["field", "value"])


@auth.command("setup")
def auth_setup():
    """Interactive setup wizard — walks you through full configuration."""
    from pathlib import Path as _Path

    click.secho("\n  ╔══════════════════════════════════════════╗", fg="cyan")
    click.secho("  ║   gads-cli — Setup Wizard     ║", fg="cyan")
    click.secho("  ╚══════════════════════════════════════════╝\n", fg="cyan")

    # ── Step 0: Determine scope ──────────────────────────────
    # Project-local if CWD has .env/.env.example or GADS_PROJECT_ROOT is set.
    # Otherwise user-global (~/.config/gads/).
    cwd = _Path.cwd()
    explicit_root = os.environ.get("GADS_PROJECT_ROOT")
    if explicit_root:
        scope_dir = _Path(explicit_root)
        scope_label = f"project ({scope_dir})"
    elif (cwd / ".env").exists() or (cwd / ".env.example").exists() or (cwd / "data").is_dir():
        scope_dir = cwd
        scope_label = f"project ({cwd})"
    else:
        scope_dir = CONFIG_HOME
        scope_label = f"global ({CONFIG_HOME})"

    scope_dir.mkdir(parents=True, exist_ok=True)
    env_path = scope_dir / ".env"
    click.secho(f"  Scope: {scope_label}\n", fg="white", bold=True)

    # ── Step 1: .env file ────────────────────────────────────
    # Look for .env.example in the CLI package directory
    pkg_dir = _Path(__file__).resolve().parent.parent
    env_example = pkg_dir / ".env.example"

    if env_path.exists():
        click.secho("  ✓ .env file exists", fg="green")
    else:
        click.secho("  Step 1: Create .env configuration file\n", fg="white", bold=True)
        if env_example.exists():
            import shutil
            shutil.copy(env_example, env_path)
            click.secho(f"  ✓ Created .env from template at {env_path}", fg="green")
        else:
            env_path.touch()
            click.secho(f"  ✓ Created empty .env at {env_path}", fg="green")
        click.echo()

    # ── Step 2: Google Cloud project ─────────────────────────
    click.secho("  Step 2: Google Cloud Project & APIs\n", fg="white", bold=True)
    click.echo("  You need a Google Cloud project. If you don't have one:")
    click.echo("    1. Go to:")
    click.secho("       https://console.cloud.google.com/projectcreate", fg="blue")
    click.echo("    2. Name it anything (e.g. 'gads-cli')")
    click.echo("    3. Click 'CREATE'\n")
    click.echo("  Then enable the APIs you need. Click each link → click 'ENABLE':")
    click.echo()
    apis = [
        ("Google Ads API",               "https://console.cloud.google.com/apis/library/googleads.googleapis.com",                          "Required", "Campaign management, reporting, GAQL queries"),
        ("My Business Account Mgmt API", "https://console.cloud.google.com/apis/library/mybusinessaccountmanagement.googleapis.com",        "For GBP",  "List accounts, manage locations"),
        ("My Business Business Info API", "https://console.cloud.google.com/apis/library/mybusinessbusinessinformation.googleapis.com",     "For GBP",  "Location details, hours, attributes"),
        ("My Business v4 (legacy)",       "https://console.cloud.google.com/apis/library/mybusiness.googleapis.com",                        "For GBP",  "Reviews, posts, media, Q&A"),
        ("Content API for Shopping",      "https://console.cloud.google.com/apis/library/content.googleapis.com",                           "For MC",   "Products, feeds, shipping, returns"),
        ("GA4 Data API",                  "https://console.cloud.google.com/apis/library/analyticsdata.googleapis.com",                     "For GA4",  "Reports, realtime data"),
        ("GA4 Admin API",                 "https://console.cloud.google.com/apis/library/analyticsadmin.googleapis.com",                    "For GA4",  "Property metadata, account structure"),
    ]
    for name, url, scope, desc in apis:
        click.echo(f"    • {name}")
        click.secho(f"      {url}", fg="blue")
        click.secho(f"      [{scope}] {desc}", fg="white", dim=True)
        click.echo()
    click.echo("  ℹ  You only need to enable the APIs for services you'll use.")
    click.echo("     Google Ads API is required. The others are optional.\n")
    click.pause("  Press Enter when APIs are enabled...")
    click.echo()

    # ── Step 3: OAuth consent screen + credentials ───────────
    click.secho("  Step 3: OAuth Consent Screen & Client Credentials\n", fg="white", bold=True)
    creds_dir = CREDS_PATH.parent
    client_secret = creds_dir / "client_secret.json"

    if client_secret.exists():
        click.secho("  ✓ client_secret.json found", fg="green")
    else:
        click.echo("  First, configure the OAuth consent screen:")
        click.echo("    1. Go to:")
        click.secho("       https://console.cloud.google.com/apis/credentials/consent", fg="blue")
        click.echo("    2. User Type: 'External' (unless you have Google Workspace)")
        click.echo("    3. App name: anything (e.g. 'gads-cli')")
        click.echo("    4. User support email: your email")
        click.echo("    5. Developer contact: your email")
        click.echo("    6. Click 'SAVE AND CONTINUE' through Scopes and Test Users")
        click.echo("    7. On Test Users, add your Google account email")
        click.echo("    8. Click 'SAVE AND CONTINUE' → 'BACK TO DASHBOARD'\n")
        click.echo("  Then create OAuth credentials:")
        click.echo("    1. Go to:")
        click.secho("       https://console.cloud.google.com/apis/credentials", fg="blue")
        click.echo("    2. Click '+ CREATE CREDENTIALS' → 'OAuth client ID'")
        click.echo("    3. Application type: 'Desktop app'")
        click.echo("    4. Name it anything (e.g. 'gads-cli')")
        click.echo("    5. Click 'CREATE', then 'DOWNLOAD JSON'")
        click.echo(f"    6. Save the downloaded file as:")
        click.secho(f"       {client_secret}\n", fg="yellow")
        click.secho("  ⚠  Your app will be in 'Testing' mode. This is fine —", fg="yellow")
        click.secho("     it means only users you added as test users can log in.", fg="yellow")
        click.secho("     You do NOT need to publish or verify the app.\n", fg="yellow")
        creds_dir.mkdir(parents=True, exist_ok=True)
        click.pause("  Press Enter when client_secret.json is saved...")

        if not client_secret.exists():
            click.secho(f"\n  ✗ client_secret.json still not found at {client_secret}", fg="red")
            click.echo("  Please save it and re-run 'gads auth setup'.")
            raise SystemExit(1)

    click.secho("  ✓ client_secret.json ready\n", fg="green")

    # ── Step 4: Developer token ──────────────────────────────
    click.secho("  Step 4: Google Ads Developer Token\n", fg="white", bold=True)
    if DEV_TOKEN:
        click.secho("  ✓ GOOGLE_ADS_DEVELOPER_TOKEN is set", fg="green")
    else:
        click.echo("  ⚠  Developer tokens are created from a MANAGER (MCC) account,")
        click.echo("     NOT from your regular Google Ads account.\n")
        click.echo("  If you don't have a manager account yet:")
        click.echo("    1. Go to:")
        click.secho("       https://ads.google.com/intl/en/home/tools/manager-accounts/", fg="blue")
        click.echo("    2. Create a manager account (free, takes 2 minutes)")
        click.echo("    3. Link your Google Ads account(s) to it")
        click.echo("    4. Then go to API Center in the manager account:\n")
        click.echo("  The developer token controls your API access level:\n")
        click.echo("    ┌──────────────────────────────────────────────────────────┐")
        click.echo("    │  TEST ACCOUNT TOKEN  (instant, no approval needed)      │")
        click.echo("    │  • Works immediately for test accounts only             │")
        click.echo("    │  • Cannot access real production accounts               │")
        click.echo("    │                                                         │")
        click.echo("    │  BASIC ACCESS  (apply, usually approved in 1-3 days)    │")
        click.echo("    │  • Campaign management, reporting, audience management  │")
        click.echo("    │  • Most commands in this CLI work with Basic Access     │")
        click.echo("    │                                                         │")
        click.echo("    │  STANDARD ACCESS  (apply, may take weeks for approval)  │")
        click.echo("    │  • Required for: Keyword Planner, Keyword Forecasting,  │")
        click.echo("    │    Reach Planner, Content API, Bidding strategies API   │")
        click.echo("    │  • Google reviews your API usage before granting        │")
        click.echo("    └──────────────────────────────────────────────────────────┘\n")
        click.echo("  To get your developer token:")
        click.echo("    1. Log into your MANAGER account (not your regular ads account)")
        click.echo("    2. Go to:")
        click.secho("       https://ads.google.com/aw/apicenter", fg="blue")
        click.echo("    3. If you see 'Apply for Basic Access' → click it and wait")
        click.echo("    4. Copy your developer token once it shows 'Approved'\n")
        click.secho("  ℹ  If you need Keyword Planner commands, apply for Standard", fg="cyan")
        click.secho("     Access after getting Basic. Google may take 1-4 weeks.\n", fg="cyan")
        token = click.prompt("  Paste your developer token (or press Enter to skip)", default="", show_default=False)
        if token.strip():
            _append_env(env_path, "GOOGLE_ADS_DEVELOPER_TOKEN", token.strip())
            click.secho("  ✓ Developer token saved to .env", fg="green")
        else:
            click.secho("  ⚠ Skipped — add GOOGLE_ADS_DEVELOPER_TOKEN to .env later", fg="yellow")
    click.echo()

    # ── Step 5: Customer ID ──────────────────────────────────
    click.secho("  Step 5: Google Ads Customer ID\n", fg="white", bold=True)
    if CUSTOMER_ID:
        click.secho(f"  ✓ GOOGLE_ADS_CUSTOMER_ID is set", fg="green")
    else:
        click.echo("  Find your customer ID:")
        click.echo("    1. Log into Google Ads: https://ads.google.com")
        click.echo("    2. Your account ID is shown at the top (XXX-XXX-XXXX)")
        click.echo("    3. Enter it below WITHOUT dashes (10 digits)\n")
        cid = click.prompt("  Customer ID (10 digits, no dashes)", default="", show_default=False)
        if cid.strip():
            clean_cid = cid.strip().replace("-", "").replace(" ", "")
            if len(clean_cid) == 10 and clean_cid.isdigit():
                _append_env(env_path, "GOOGLE_ADS_CUSTOMER_ID", clean_cid)
                click.secho("  ✓ Customer ID saved to .env", fg="green")
            else:
                click.secho(f"  ⚠ '{cid}' doesn't look like a 10-digit ID — add manually to .env", fg="yellow")
        else:
            click.secho("  ⚠ Skipped — add GOOGLE_ADS_CUSTOMER_ID to .env later", fg="yellow")
    click.echo()

    # ── Step 6: Manager account ─────────────────────────────
    click.secho("  Step 6: Manager Account ID\n", fg="white", bold=True)
    if LOGIN_CUSTOMER_ID:
        click.secho(f"  ✓ GOOGLE_ADS_LOGIN_CUSTOMER_ID is set", fg="green")
    else:
        click.echo("  This is the manager (MCC) account where your developer token")
        click.echo("  was created. It's REQUIRED if you created an MCC in Step 4.")
        click.echo("  Find it at the top of your manager account in Google Ads.\n")
        mcc = click.prompt("  Manager customer ID, 10 digits (or Enter to skip)", default="", show_default=False)
        if mcc.strip():
            clean_mcc = mcc.strip().replace("-", "").replace(" ", "")
            if len(clean_mcc) == 10 and clean_mcc.isdigit():
                _append_env(env_path, "GOOGLE_ADS_LOGIN_CUSTOMER_ID", clean_mcc)
                click.secho("  ✓ Manager ID saved to .env", fg="green")
            else:
                click.secho(f"  ⚠ '{mcc}' doesn't look like a 10-digit ID — add manually to .env", fg="yellow")
        else:
            click.secho("  ⚠ Skipped — if API calls fail with auth errors, set this", fg="yellow")
    click.echo()

    # ── Step 7: Optional services ────────────────────────────
    click.secho("  Step 7: Optional Services\n", fg="white", bold=True)

    if not MERCHANT_CENTER_ID:
        click.echo("  Merchant Center ID (for product management):")
        click.echo("  Find it at: https://merchants.google.com → Settings → Account\n")
        mc_id = click.prompt("  Merchant Center ID (or Enter to skip)", default="", show_default=False)
        if mc_id.strip():
            _append_env(env_path, "GOOGLE_MERCHANT_CENTER_ID", mc_id.strip())
            click.secho("  ✓ Merchant Center ID saved", fg="green")
    else:
        click.secho("  ✓ GOOGLE_MERCHANT_CENTER_ID is set", fg="green")

    click.echo()

    if not GA4_PROPERTY_ID:
        click.echo("  GA4 Property ID (for analytics reporting):")
        click.echo("  Find it at: GA4 → Admin → Property Settings → Property ID\n")
        ga4 = click.prompt("  GA4 Property ID (or Enter to skip)", default="", show_default=False)
        if ga4.strip():
            _append_env(env_path, "GOOGLE_GA4_PROPERTY_ID", ga4.strip())
            click.secho("  ✓ GA4 Property ID saved", fg="green")
    else:
        click.secho("  ✓ GOOGLE_GA4_PROPERTY_ID is set", fg="green")

    click.echo()

    # ── Step 8: Timezone & Currency ────────────────────────────
    click.secho("  Step 8: Timezone & Currency\n", fg="white", bold=True)
    click.echo(f"  Current timezone: {TZ_NAME}")
    click.echo("  Use IANA format (e.g. America/New_York, Europe/London, Asia/Dubai)\n")
    tz = click.prompt("  Timezone (or Enter to keep current)", default=TZ_NAME, show_default=False)
    if tz.strip() and tz.strip() != TZ_NAME:
        _append_env(env_path, "GADS_TIMEZONE", tz.strip())
        click.secho(f"  ✓ Timezone set to {tz.strip()}", fg="green")
    click.echo()

    click.echo(f"  Current currency: {CURRENCY}")
    click.echo("  Use ISO 4217 code (e.g. USD, AED, EUR, GBP)\n")
    cur = click.prompt("  Currency (or Enter to keep current)", default=CURRENCY, show_default=False)
    if cur.strip().upper() and cur.strip().upper() != CURRENCY:
        _append_env(env_path, "GADS_CURRENCY", cur.strip().upper())
        click.secho(f"  ✓ Currency set to {cur.strip().upper()}", fg="green")
    click.echo()

    # ── Step 9: OAuth login ──────────────────────────────────
    click.secho("  Step 9: Authenticate with Google\n", fg="white", bold=True)
    if CREDS_PATH.exists():
        click.secho("  ✓ OAuth token exists", fg="green")
        reauth = click.confirm("  Re-authenticate anyway?", default=False)
        if not reauth:
            click.echo()
            _finish_setup()
            return

    click.echo("  Opening browser for Google sign-in...")
    click.echo("  You'll be asked to grant access to Google Ads, Business Profile,")
    click.echo("  Merchant Center, and Google Analytics.\n")

    _do_oauth_login(client_secret, CREDS_PATH)

    click.echo()
    _finish_setup()


@auth.command("login")
@click.option("--port", type=int, default=9090, help="Local OAuth callback port.")
@click.option("--force", is_flag=True, help="Re-authenticate even if token exists.")
def auth_login(port, force):
    """Authenticate with Google (OAuth browser flow)."""
    client_secret = CREDS_PATH.parent / "client_secret.json"

    if not client_secret.exists():
        click.secho(f"✗ client_secret.json not found at {client_secret}", fg="red", err=True)
        click.echo("\n  To get it:")
        click.echo("    1. Go to https://console.cloud.google.com/apis/credentials")
        click.echo("    2. Create an OAuth 2.0 Client ID (Desktop app)")
        click.echo("    3. Download the JSON and save as:")
        click.secho(f"       {client_secret}", fg="yellow")
        click.echo("\n  Or run 'gads auth setup' for the full guided wizard.")
        raise SystemExit(1)

    if CREDS_PATH.exists() and not force:
        click.secho("  Token already exists. Use --force to re-authenticate.", fg="yellow")
        click.echo(f"  Token: {CREDS_PATH}")
        return

    _do_oauth_login(client_secret, CREDS_PATH, port=port)


@auth.command("revoke")
@click.confirmation_option(prompt="This will delete your OAuth token. Continue?")
def auth_revoke():
    """Revoke and delete the stored OAuth token."""
    if CREDS_PATH.exists():
        # Try to revoke with Google first
        try:
            import json as _json
            import requests as _requests
            with open(CREDS_PATH) as f:
                token_data = _json.load(f)
            token = token_data.get("token", "")
            if token:
                resp = _requests.post(
                    "https://oauth2.googleapis.com/revoke",
                    params={"token": token},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                if resp.status_code == 200:
                    click.secho("  ✓ Token revoked with Google", fg="green")
                else:
                    click.secho("  ⚠ Could not revoke with Google (token may be expired)", fg="yellow")
        except Exception:
            pass

        CREDS_PATH.unlink()
        click.secho(f"  ✓ Deleted {CREDS_PATH}", fg="green")
    else:
        click.echo("  No token to revoke.")


@auth.command("test")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def auth_test(as_json):
    """Test API access for all configured services."""
    results = []

    # Test Google Ads
    if CUSTOMER_ID and DEV_TOKEN:
        try:
            creds = get_credentials()
            rows = run_gaql(creds, "SELECT customer.id FROM customer LIMIT 1")
            results.append({"service": "Google Ads", "status": "ok", "detail": f"Customer {CUSTOMER_ID} accessible"})
        except Exception as e:
            results.append({"service": "Google Ads", "status": "fail", "detail": str(e)[:100]})
    else:
        results.append({"service": "Google Ads", "status": "skip", "detail": "CUSTOMER_ID or DEV_TOKEN not set"})

    # Test GBP
    try:
        creds = get_credentials()
        accts = gbp_list_accounts(creds)
        count = len(accts) if isinstance(accts, list) else 0
        results.append({"service": "Google Business Profile", "status": "ok", "detail": f"{count} account(s) found"})
    except Exception as e:
        msg = str(e)[:100]
        if "403" in msg:
            results.append({"service": "Google Business Profile", "status": "fail", "detail": "403 — re-run 'gads auth login --force' to add scope"})
        else:
            results.append({"service": "Google Business Profile", "status": "fail", "detail": msg})

    # Test Merchant Center
    if MERCHANT_CENTER_ID:
        try:
            creds = get_credentials()
            mc_get_account(creds)
            results.append({"service": "Merchant Center", "status": "ok", "detail": f"Account {MERCHANT_CENTER_ID} accessible"})
        except Exception as e:
            results.append({"service": "Merchant Center", "status": "fail", "detail": str(e)[:100]})
    else:
        results.append({"service": "Merchant Center", "status": "skip", "detail": "GOOGLE_MERCHANT_CENTER_ID not set"})

    # Test GA4
    if GA4_PROPERTY_ID:
        try:
            creds = get_credentials()
            ga4_get_metadata(creds, GA4_PROPERTY_ID)
            results.append({"service": "GA4", "status": "ok", "detail": f"Property {GA4_PROPERTY_ID} accessible"})
        except Exception as e:
            msg = str(e)[:100]
            if "403" in msg:
                results.append({"service": "GA4", "status": "fail", "detail": "403 — enable Analytics API or re-run 'gads auth login --force'"})
            else:
                results.append({"service": "GA4", "status": "fail", "detail": msg})
    else:
        results.append({"service": "GA4", "status": "skip", "detail": "GOOGLE_GA4_PROPERTY_ID not set"})

    if as_json:
        print_json(results)
        return

    click.secho("\n  API Access Test\n", fg="white", bold=True)
    print_table(results, ["service", "status", "detail"])
    failures = [r for r in results if r["status"] == "fail"]
    if failures:
        click.echo()
        click.secho("  Tip: Run 'gads auth login --force' to re-authenticate with all scopes.", fg="yellow")
        raise SystemExit(1)


# ── Auth helpers ─────────────────────────────────────────────


def _append_env(env_path, key, value):
    """Append or update a key in the .env file."""
    lines = []
    found = False
    if env_path.exists():
        with open(env_path) as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(f"{key}=") or stripped.startswith(f"# {key}="):
                lines[i] = f"{key}={value}\n"
                found = True
                break
    if not found:
        lines.append(f"{key}={value}\n")
    with open(env_path, "w") as f:
        f.writelines(lines)


def _do_oauth_login(client_secret_path, token_output_path, port=9090):
    """Run the OAuth browser flow and save the token."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    SCOPES = [
        "https://www.googleapis.com/auth/adwords",
        "https://www.googleapis.com/auth/business.manage",
        "https://www.googleapis.com/auth/content",
        "https://www.googleapis.com/auth/analytics.readonly",
    ]

    token_output_path.parent.mkdir(parents=True, exist_ok=True)

    flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_path), SCOPES)

    click.echo(f"  Listening on port {port} for OAuth callback...")
    try:
        creds = flow.run_local_server(port=port, prompt="consent", access_type="offline")
    except Exception as e:
        click.secho(f"\n  ✗ OAuth flow failed: {e}", fg="red", err=True)
        click.echo("  Make sure no other process is using port {port}.")
        click.echo("  You can also try: gads auth login --port 8888")
        raise SystemExit(1)

    with open(token_output_path, "w") as f:
        f.write(creds.to_json())

    click.secho(f"  ✓ Token saved to {token_output_path}", fg="green")

    # Verify scopes
    granted = sorted(list(creds.scopes or []))
    scope_names = {
        "https://www.googleapis.com/auth/adwords": "Google Ads",
        "https://www.googleapis.com/auth/business.manage": "Business Profile",
        "https://www.googleapis.com/auth/content": "Merchant Center",
        "https://www.googleapis.com/auth/analytics.readonly": "GA4 Analytics",
    }
    click.echo("  Scopes granted:")
    for scope in SCOPES:
        name = scope_names.get(scope, scope)
        if scope in granted:
            click.secho(f"    ✓ {name}", fg="green")
        else:
            click.secho(f"    ✗ {name} — not granted", fg="red")


def _finish_setup():
    """Print final setup summary."""
    click.secho("  ╔══════════════════════════════════════════╗", fg="green")
    click.secho("  ║         Setup Complete!                  ║", fg="green")
    click.secho("  ╚══════════════════════════════════════════╝\n", fg="green")
    click.echo("  Next steps:")
    click.echo("    1. Run:  gads doctor        — verify configuration")
    click.echo("    2. Run:  gads auth test     — test API access")
    click.echo("    3. Run:  gads query \"SELECT customer.id FROM customer\"")
    click.echo("    4. Run:  gads refresh       — populate local database")
    click.echo()


@cli.command()
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def doctor(as_json):
    """Run local CLI readiness checks."""
    checks = [
        {"check": "scope", "status": "ok", "detail": f"{SCOPE_TYPE} → {SCOPE_ROOT}"},
        {"check": "credentials", "status": "ok" if CREDS_PATH.exists() else "fail", "detail": str(CREDS_PATH)},
        {"check": "database", "status": "ok" if DB_PATH.exists() else "fail", "detail": str(DB_PATH)},
        {"check": "developer_token", "status": "ok" if DEV_TOKEN else "fail", "detail": "set" if DEV_TOKEN else "missing — set GOOGLE_ADS_DEVELOPER_TOKEN"},
        {"check": "customer_id", "status": "ok" if CUSTOMER_ID else "fail", "detail": "set" if CUSTOMER_ID else "missing — set GOOGLE_ADS_CUSTOMER_ID"},
        {"check": "login_customer_id", "status": "ok" if LOGIN_CUSTOMER_ID else "warn", "detail": "set" if LOGIN_CUSTOMER_ID else "missing (optional for non-MCC)"},
        {"check": "merchant_center_id", "status": "ok" if MERCHANT_CENTER_ID else "warn", "detail": "set" if MERCHANT_CENTER_ID else "missing (optional)"},
        {"check": "ga4_property_id", "status": "ok" if GA4_PROPERTY_ID else "warn", "detail": "set" if GA4_PROPERTY_ID else "missing (optional)"},
        {"check": "timezone", "status": "ok", "detail": TZ_NAME},
        {"check": "currency", "status": "ok", "detail": CURRENCY},
    ]

    if as_json:
        print_json(checks)
        return

    click.secho("\n  gads doctor\n", fg="white", bold=True)
    print_table(checks, ["check", "status", "detail"])
    failures = [c for c in checks if c["status"] == "fail"]
    if failures:
        raise SystemExit(1)


# ── Google Ads commands ──────────────────────────────────────


@cli.command()
@click.argument("gaql")
@click.option("--limit", "-l", type=int, default=None, help="Max rows.")
@click.option("--json", "as_json", is_flag=True)
def query(gaql, limit, as_json):
    """Run a GAQL query against the Google Ads API."""
    creds = get_credentials()
    results = run_gaql(creds, gaql)
    if limit:
        results = results[:limit]
    if as_json:
        print_json(results)
        return
    if not results:
        click.echo("  (no results)")
        return
    flat_rows = [flatten(r) for r in results]
    print_table(flat_rows)
    click.echo(f"\n  {len(flat_rows)} row(s)")


@cli.command()
@click.argument("action")
@click.argument("details")
@click.option("--reason", "-r", default="")
@click.option("--campaign", "-c", default="")
@click.option("--campaign-id", default="")
@click.option("--agent", default="claude-code")
@click.option("--snapshot-ref", default="")
@click.option("--script", default="")
def log(action, details, reason, campaign, campaign_id, agent, snapshot_ref, script):
    """Log an action to the changelog (append-only)."""
    import json as _json
    ts = now_local()
    conn = get_db()
    raw = {"timestamp": ts, "action": action, "campaign": campaign,
           "campaign_id": campaign_id, "details": details, "reason": reason,
           "agent": agent, "snapshot_ref": snapshot_ref, "script": script}
    try:
        conn.execute(
            """INSERT INTO changelog
            (timestamp, action, campaign, campaign_id, details, reason, agent, snapshot_ref, script, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (ts, action, campaign, campaign_id, details, reason, agent, snapshot_ref, script, _json.dumps(raw)),
        )
        conn.commit()
        click.secho(f"✓ Logged: {action} at {ts}", fg="green")
    finally:
        conn.close()


@cli.command()
@click.argument("name")
@click.option("--save-file", is_flag=True, help="Also save JSON to snapshots/ directory.")
def snapshot(name, save_file):
    """Snapshot current campaign configs from the API."""
    import json as _json
    creds = get_credentials()
    gaql = """
    SELECT campaign.name, campaign.id, campaign.status,
           campaign.advertising_channel_type, campaign_budget.amount_micros,
           campaign.bidding_strategy_type,
           campaign.target_cpa.target_cpa_micros, campaign.target_roas.target_roas
    FROM campaign WHERE campaign.status != 'REMOVED' ORDER BY campaign.name
    """
    click.echo("Fetching campaign configs from API...")
    results = run_gaql(creds, gaql)
    configs = []
    for r in results:
        camp = r.get("campaign", {})
        budget = r.get("campaignBudget", {})
        configs.append({
            "campaign_name": camp.get("name", ""), "campaign_id": camp.get("id", ""),
            "status": camp.get("status", ""), "channel_type": camp.get("advertisingChannelType", ""),
            "budget": int(budget.get("amountMicros", 0)) / 1_000_000,
            "bidding_strategy": camp.get("biddingStrategyType", ""),
            "target_cpa": int(camp.get("targetCpa", {}).get("targetCpaMicros", 0)) / 1_000_000,
            "target_roas": float(camp.get("targetRoas", {}).get("targetRoas", 0)),
        })

    click.echo(f"  Got {len(configs)} campaigns")
    conn = get_db()
    today = today_local()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{ts}_{name}.json"

    for cfg in configs:
        conn.execute(
            """INSERT OR REPLACE INTO campaign_config
            (snapshot_date, campaign_name, campaign_id, channel_type, status,
             budget, bidding_strategy, target_cpa, target_roas)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (today, cfg["campaign_name"], cfg["campaign_id"], cfg["channel_type"],
             cfg["status"], cfg["budget"], cfg["bidding_strategy"],
             cfg["target_cpa"], cfg["target_roas"]),
        )
    conn.execute("INSERT OR REPLACE INTO snapshots VALUES (?, ?, ?, ?, ?)",
                 (filename, today, datetime.now().strftime("%H:%M:%S"), name, ""))
    conn.commit()
    conn.close()
    click.secho(f"✓ Saved {len(configs)} configs (date={today})", fg="green")

    if save_file:
        SNAPSHOTS_DIR.mkdir(exist_ok=True)
        filepath = SNAPSHOTS_DIR / filename
        with open(filepath, "w") as f:
            _json.dump({"name": name, "date": today, "campaigns": configs}, f, indent=2)
        click.secho(f"✓ Written: {filepath}", fg="green")


@cli.command()
@click.option("--days", "-d", type=int, default=7)
@click.option("--campaign", "-c", default=None)
@click.option("--json", "as_json", is_flag=True)
def perf(days, campaign, as_json):
    """Performance summary from the local database."""
    conn = get_db()
    date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    date_to = today_local()

    where = "WHERE date >= ? AND date <= ?"
    params = [date_from, date_to]
    if campaign:
        where += " AND campaign_name LIKE ?"
        params.append(f"%{campaign}%")

    q_daily = f"""
    SELECT date, SUM(impressions) AS impressions, SUM(clicks) AS clicks,
           SUM(conversions) AS conversions, SUM(cost) AS cost,
           CASE WHEN SUM(conversions)>0 THEN SUM(cost)/SUM(conversions) END AS cpa,
           CASE WHEN SUM(impressions)>0 THEN CAST(SUM(clicks) AS REAL)/SUM(impressions)*100 END AS ctr,
           CASE WHEN SUM(clicks)>0 THEN SUM(conversions)/CAST(SUM(clicks) AS REAL)*100 END AS cvr
    FROM daily_performance {where} GROUP BY date ORDER BY date
    """
    daily_rows = [dict(r) for r in conn.execute(q_daily, params).fetchall()]

    q_camp = f"""
    SELECT campaign_name, SUM(impressions) AS impressions, SUM(clicks) AS clicks,
           SUM(conversions) AS conversions, SUM(cost) AS cost,
           CASE WHEN SUM(conversions)>0 THEN SUM(cost)/SUM(conversions) END AS cpa,
           CASE WHEN SUM(impressions)>0 THEN CAST(SUM(clicks) AS REAL)/SUM(impressions)*100 END AS ctr,
           CASE WHEN SUM(clicks)>0 THEN SUM(conversions)/CAST(SUM(clicks) AS REAL)*100 END AS cvr
    FROM daily_performance {where} GROUP BY campaign_name ORDER BY SUM(conversions) DESC
    """
    camp_rows = [dict(r) for r in conn.execute(q_camp, params).fetchall()]
    conn.close()

    if as_json:
        print_json({"period": f"{date_from} to {date_to}", "daily": daily_rows, "by_campaign": camp_rows})
        return

    cols = ["date", "impressions", "clicks", "conversions", "cost", "cpa", "ctr", "cvr"]
    click.secho(f"\n  Performance: {date_from} → {date_to}\n", fg="white", bold=True)
    click.secho("  Daily:", bold=True)
    print_table(daily_rows, cols)
    click.echo()
    click.secho("  By Campaign:", bold=True)
    print_table(camp_rows, ["campaign_name"] + cols[1:])


@cli.command()
@click.option("--json", "as_json", is_flag=True)
@click.option("--from-db", is_flag=True)
def config(as_json, from_db):
    """Show current campaign configurations."""
    if from_db:
        conn = get_db()
        row = conn.execute("SELECT MAX(snapshot_date) FROM campaign_config").fetchone()
        snap_date = row[0] if row else None
        if not snap_date:
            click.secho("✗ No snapshots. Run: gads snapshot <name>", fg="red", err=True)
            raise SystemExit(1)
        rows = conn.execute(
            "SELECT * FROM campaign_config WHERE snapshot_date = ? ORDER BY campaign_name",
            (snap_date,),
        ).fetchall()
        configs = [dict(r) for r in rows]
        conn.close()
    else:
        creds = get_credentials()
        gaql = """
        SELECT campaign.name, campaign.id, campaign.status,
               campaign.advertising_channel_type, campaign_budget.amount_micros,
               campaign.bidding_strategy_type,
               campaign.target_cpa.target_cpa_micros, campaign.target_roas.target_roas
        FROM campaign WHERE campaign.status != 'REMOVED' ORDER BY campaign.name
        """
        results = run_gaql(creds, gaql)
        configs = []
        for r in results:
            camp = r.get("campaign", {})
            budget = r.get("campaignBudget", {})
            configs.append({
                "campaign_name": camp.get("name", ""), "status": camp.get("status", ""),
                "channel_type": camp.get("advertisingChannelType", ""),
                "budget": int(budget.get("amountMicros", 0)) / 1_000_000,
                "bidding_strategy": camp.get("biddingStrategyType", ""),
                "target_cpa": int(camp.get("targetCpa", {}).get("targetCpaMicros", 0)) / 1_000_000 or None,
                "target_roas": float(camp.get("targetRoas", {}).get("targetRoas", 0)) or None,
            })
    if as_json:
        print_json(configs)
        return
    click.secho("\n  Campaign Configurations\n", fg="white", bold=True)
    print_table(configs, ["campaign_name", "status", "channel_type", "budget", "bidding_strategy", "target_cpa", "target_roas"])
    click.echo(f"\n  {len(configs)} campaign(s)")


@cli.command()
@click.option("--days", "-d", type=int, default=3)
@click.option("--config", "with_config", is_flag=True)
@click.option("--push", is_flag=True)
def refresh(days, with_config, push):
    """Pull fresh data from the API into the local database."""
    date_to = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    click.echo(f"Fetching: {date_from} → {date_to}")
    creds = get_credentials()

    q = f"""
    SELECT segments.date, campaign.name, campaign.id, campaign.status,
           campaign.advertising_channel_type, metrics.cost_micros,
           metrics.conversions, metrics.clicks, metrics.impressions,
           metrics.conversions_value, metrics.all_conversions, metrics.interactions
    FROM campaign WHERE segments.date BETWEEN '{date_from}' AND '{date_to}'
    ORDER BY segments.date, campaign.name
    """
    results = run_gaql(creds, q)
    rows = []
    for r in results:
        seg, camp, m = r.get("segments", {}), r.get("campaign", {}), r.get("metrics", {})
        rows.append((
            seg.get("date", ""), camp.get("name", ""), camp.get("id", ""),
            camp.get("advertisingChannelType", ""), camp.get("status", ""),
            int(m.get("impressions", 0)), int(m.get("clicks", 0)),
            float(m.get("conversions", 0)), int(m.get("costMicros", 0)) / 1_000_000,
            float(m.get("conversionsValue", 0)), float(m.get("allConversions", 0)),
            int(m.get("interactions", 0)),
        ))

    conn = get_db()
    for row in rows:
        conn.execute(
            """INSERT OR REPLACE INTO daily_performance
            (date, campaign_name, campaign_id, channel_type, status,
             impressions, clicks, conversions, cost, conv_value,
             all_conversions, interactions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", row)
    conn.commit()
    click.secho(f"  ✓ {len(rows)} rows updated", fg="green")

    if with_config:
        cfg_q = """
        SELECT campaign.name, campaign.id, campaign.status,
               campaign.advertising_channel_type, campaign_budget.amount_micros,
               campaign.bidding_strategy_type,
               campaign.target_cpa.target_cpa_micros, campaign.target_roas.target_roas
        FROM campaign WHERE campaign.status != 'REMOVED' ORDER BY campaign.name
        """
        today = today_local()
        for r in run_gaql(creds, cfg_q):
            camp, budget = r.get("campaign", {}), r.get("campaignBudget", {})
            conn.execute(
                """INSERT OR REPLACE INTO campaign_config
                (snapshot_date, campaign_name, campaign_id, channel_type, status,
                 budget, bidding_strategy, target_cpa, target_roas)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (today, camp.get("name", ""), camp.get("id", ""),
                 camp.get("advertisingChannelType", ""), camp.get("status", ""),
                 int(budget.get("amountMicros", 0)) / 1_000_000,
                 camp.get("biddingStrategyType", ""),
                 int(camp.get("targetCpa", {}).get("targetCpaMicros", 0)) / 1_000_000,
                 float(camp.get("targetRoas", {}).get("targetRoas", 0))))
        conn.commit()
        click.secho("  ✓ Campaign configs updated", fg="green")
    conn.close()

    if push:
        os.chdir(str(PROJECT_ROOT))
        subprocess.run(["git", "add", str(DB_PATH)], check=True)
        subprocess.run(["git", "commit", "-m", f"data: refresh {date_from} to {date_to}"], check=False)
        subprocess.run(["git", "pull", "--rebase"], check=False)
        subprocess.run(["git", "push"], check=False)
        click.secho("  ✓ Git sync done", fg="green")


# ── GBP commands ─────────────────────────────────────────────

@gbp.command("accounts")
@click.option("--json", "as_json", is_flag=True)
def gbp_accounts(as_json):
    """List accessible Business Profile accounts."""
    enforce_allowed_caller()
    data = gbp_list_accounts(get_credentials())
    accounts = data.get("accounts", [])
    if as_json: return print_json(accounts)
    rows = [{"name": a.get("name",""), "account_name": a.get("accountName",""),
             "type": a.get("type",""), "role": a.get("role","")} for a in accounts]
    print_table(rows, ["name", "account_name", "type", "role"])

@gbp.command("locations")
@click.option("--account", "account_name", required=True)
@click.option("--json", "as_json", is_flag=True)
def gbp_locations(account_name, as_json):
    """List locations for an account."""
    enforce_allowed_caller()
    data = gbp_list_locations(get_credentials(), account_name,
        read_mask="name,title,storeCode,phoneNumbers,websiteUri,languageCode,storefrontAddress,metadata")
    locations = data.get("locations", [])
    if as_json: return print_json(locations)
    rows = []
    for loc in locations:
        phone = ((loc.get("phoneNumbers") or {}).get("primaryPhone")) or ""
        addr = ((loc.get("storefrontAddress") or {}).get("addressLines") or [""])
        rows.append({"name": loc.get("name",""), "title": loc.get("title",""),
                     "phone": phone, "website": loc.get("websiteUri",""),
                     "address": ", ".join(a for a in addr if a)})
    print_table(rows, ["name", "title", "phone", "website", "address"])

@gbp.command("location")
@click.argument("location_name")
@click.option("--json", "as_json", is_flag=True)
def gbp_location(location_name, as_json):
    """Get one location detail."""
    enforce_allowed_caller()
    data = gbp_get_location(get_credentials(), location_name,
        read_mask="name,title,storeCode,phoneNumbers,websiteUri,regularHours,specialHours,serviceArea,storefrontAddress,metadata,profile,labels,languageCode")
    if as_json: return print_json(data)
    rows = [{"field": k, "value": v} for k, v in data.items() if not isinstance(v, (dict, list))]
    print_table(rows, ["field", "value"])

@gbp.command("reviews")
@click.argument("location_name")
@click.option("--json", "as_json", is_flag=True)
def gbp_reviews(location_name, as_json):
    """List reviews for a location."""
    enforce_allowed_caller()
    data = gbp_list_reviews(get_credentials(), location_name)
    reviews = data.get("reviews", [])
    if as_json: return print_json(reviews)
    rows = [{"name": r.get("name",""), "reviewer": ((r.get("reviewer") or {}).get("displayName")) or "",
             "stars": r.get("starRating",""),
             "comment": (r.get("comment","")[:80]+"…") if len(r.get("comment",""))>80 else r.get("comment",""),
             "reply": ((r.get("reviewReply") or {}).get("comment")) or "",
             "updated": r.get("updateTime","")} for r in reviews]
    print_table(rows, ["name", "reviewer", "stars", "comment", "reply", "updated"])

@gbp.command("reply-review")
@click.argument("review_name")
@click.argument("comment")
def gbp_reply_review_cmd(review_name, comment):
    """Reply to a review."""
    enforce_allowed_caller()
    print_json(gbp_reply_review(get_credentials(), review_name, comment))

@gbp.command("delete-reply")
@click.argument("review_name")
def gbp_delete_reply_cmd(review_name):
    """Delete a review reply."""
    enforce_allowed_caller()
    gbp_delete_reply(get_credentials(), review_name)
    click.secho(f"✓ Reply deleted", fg="green")

# ── Merchant commands ────────────────────────────────────────

@merchant.command("account")
@click.option("--json", "as_json", is_flag=True)
def merchant_account(as_json):
    """Account info."""
    enforce_allowed_caller()
    data = mc_get_account(get_credentials())
    if as_json: return print_json(data)
    rows = [{"field": k, "value": v} for k, v in data.items() if not isinstance(v, (dict, list))]
    print_table(rows, ["field", "value"])

@merchant.command("status")
@click.option("--json", "as_json", is_flag=True)
def merchant_status(as_json):
    """Account issues."""
    enforce_allowed_caller()
    data = mc_get_account_status(get_credentials())
    if as_json: return print_json(data)
    issues = data.get("accountLevelIssues", [])
    if not issues: return click.secho("  No issues.", fg="green")
    rows = [{"id": i.get("id",""), "severity": i.get("severity",""), "title": i.get("title",""),
             "detail": (i.get("detail","")[:80]+"…") if len(i.get("detail",""))>80 else i.get("detail","")}
            for i in issues]
    print_table(rows, ["id", "severity", "title", "detail"])

@merchant.command("products")
@click.option("--limit", "-l", type=int, default=20)
@click.option("--json", "as_json", is_flag=True)
def merchant_products(limit, as_json):
    """List products."""
    enforce_allowed_caller()
    data = mc_list_products(get_credentials(), max_results=limit)
    products = data.get("resources", [])
    if as_json: return print_json(products)
    rows = [{"id": p.get("id",""),
             "title": (p.get("title","")[:50]+"…") if len(p.get("title",""))>50 else p.get("title",""),
             "channel": p.get("channel",""), "availability": p.get("availability",""),
             "price": f"{p.get('price',{}).get('value','')} {p.get('price',{}).get('currency','')}"} for p in products]
    print_table(rows, ["id", "title", "channel", "availability", "price"])

@merchant.command("product-status")
@click.option("--limit", "-l", type=int, default=20)
@click.option("--json", "as_json", is_flag=True)
def merchant_product_status(limit, as_json):
    """Product approval statuses."""
    enforce_allowed_caller()
    data = mc_list_product_statuses(get_credentials(), max_results=limit)
    statuses = data.get("resources", [])
    if as_json: return print_json(statuses)
    rows = [{"product_id": s.get("productId",""),
             "title": (s.get("title","")[:40]+"…") if len(s.get("title",""))>40 else s.get("title",""),
             "destinations": ", ".join(f"{d.get('destination','')}: {d.get('status','')}" for d in s.get("destinationStatuses",[])[:3]),
             "issues": len(s.get("itemLevelIssues",[]))} for s in statuses]
    print_table(rows, ["product_id", "title", "destinations", "issues"])

@merchant.command("feeds")
@click.option("--json", "as_json", is_flag=True)
def merchant_feeds(as_json):
    """Data feeds."""
    enforce_allowed_caller()
    data = mc_list_datafeeds(get_credentials())
    feeds = data.get("resources", [])
    if as_json: return print_json(feeds)
    rows = [{"id": f.get("id",""), "name": f.get("name",""),
             "content_type": f.get("contentType",""), "file_name": f.get("fileName") or ""} for f in feeds]
    print_table(rows, ["id", "name", "content_type", "file_name"])

@merchant.command("shipping")
@click.option("--json", "as_json", is_flag=True)
def merchant_shipping(as_json):
    """Shipping settings."""
    enforce_allowed_caller()
    data = mc_get_shipping(get_credentials())
    if as_json: return print_json(data)
    rows = [{"name": s.get("name",""), "country": s.get("deliveryCountry",""),
             "currency": s.get("currency",""), "active": s.get("active","")} for s in data.get("services",[])]
    print_table(rows, ["name", "country", "currency", "active"])

@merchant.command("returns")
@click.option("--json", "as_json", is_flag=True)
def merchant_returns(as_json):
    """Return policy."""
    enforce_allowed_caller()
    data = mc_get_return_policy(get_credentials())
    if as_json: return print_json(data)
    policies = data.get("resources", data.get("returnPolicies", [data] if "name" in data else []))
    rows = [{"name": p.get("name",""), "country": p.get("country",""),
             "label": p.get("label",""), "days": (p.get("policy") or {}).get("numberOfDays","")} for p in policies]
    print_table(rows, ["name", "country", "label", "days"])

# ── GA4 commands ─────────────────────────────────────────────

@ga4.command("metadata")
@click.option("--property", "property_id", default=None)
@click.option("--json", "as_json", is_flag=True)
def ga4_metadata_cmd(property_id, as_json):
    """Available dimensions and metrics."""
    enforce_allowed_caller()
    data = ga4_get_metadata(get_credentials(), property_id=property_id)
    if as_json: return print_json(data)
    dims, mets = data.get("dimensions",[]), data.get("metrics",[])
    click.secho(f"\n  Dimensions: {len(dims)}   Metrics: {len(mets)}\n", bold=True)
    for d in dims[:15]: click.echo(f"    {d.get('apiName','')} — {d.get('uiName','')}")
    click.echo()
    for m in mets[:15]: click.echo(f"    {m.get('apiName','')} — {m.get('uiName','')}")

@ga4.command("report")
@click.option("--property", "property_id", default=None)
@click.option("--dimensions", "-d", default="date")
@click.option("--metrics", "-m", default="activeUsers,sessions")
@click.option("--start", "start_date", default="7daysAgo")
@click.option("--end", "end_date", default="yesterday")
@click.option("--limit", "-l", type=int, default=100)
@click.option("--json", "as_json", is_flag=True)
def ga4_report_cmd(property_id, dimensions, metrics, start_date, end_date, limit, as_json):
    """Run a GA4 report."""
    enforce_allowed_caller()
    dims = [d.strip() for d in dimensions.split(",")]
    mets = [m.strip() for m in metrics.split(",")]
    data = ga4_run_report(get_credentials(), dims, mets,
        [{"startDate": start_date, "endDate": end_date}], property_id=property_id, limit=limit)
    if as_json: return print_json(data)
    dim_h = [h.get("name","") for h in data.get("dimensionHeaders",[])]
    met_h = [h.get("name","") for h in data.get("metricHeaders",[])]
    rows = []
    for row in data.get("rows",[]):
        r = {dim_h[i]: dv.get("value","") for i, dv in enumerate(row.get("dimensionValues",[]))}
        r.update({met_h[i]: mv.get("value","") for i, mv in enumerate(row.get("metricValues",[]))})
        rows.append(r)
    print_table(rows, dim_h + met_h)
    click.echo(f"\n  {len(rows)} row(s)")

@ga4.command("realtime")
@click.option("--property", "property_id", default=None)
@click.option("--dimensions", "-d", default="country")
@click.option("--metrics", "-m", default="activeUsers")
@click.option("--json", "as_json", is_flag=True)
def ga4_realtime_cmd(property_id, dimensions, metrics, as_json):
    """Realtime report (last 30 min)."""
    enforce_allowed_caller()
    dims = [d.strip() for d in dimensions.split(",")]
    mets = [m.strip() for m in metrics.split(",")]
    data = ga4_run_realtime_report(get_credentials(), dims, mets, property_id=property_id)
    if as_json: return print_json(data)
    dim_h = [h.get("name","") for h in data.get("dimensionHeaders",[])]
    met_h = [h.get("name","") for h in data.get("metricHeaders",[])]
    rows = []
    for row in data.get("rows",[]):
        r = {dim_h[i]: dv.get("value","") for i, dv in enumerate(row.get("dimensionValues",[]))}
        r.update({met_h[i]: mv.get("value","") for i, mv in enumerate(row.get("metricValues",[]))})
        rows.append(r)
    print_table(rows, dim_h + met_h)
    click.echo(f"\n  {len(rows)} row(s)")


# ── New command groups ───────────────────────────────────────

@cli.group()
def campaign():
    """Campaign management commands."""
    pass

@cli.group()
def adgroup():
    """Ad group management commands."""
    pass

@cli.group("ad")
def ad_group():
    """Ad management commands."""
    pass

@cli.group()
def keyword():
    """Keyword management and research."""
    pass

@cli.group("asset")
def asset_group():
    """Asset management (images, sitelinks, callouts)."""
    pass

@cli.group("conversion")
def conversion_group():
    """Conversion tracking and upload."""
    pass

@cli.group("audience")
def audience_group():
    """Audience and user list management."""
    pass

@cli.group("report")
def report_group():
    """Specialized reports (geo, hourly, devices, search terms)."""
    pass


# ── Helpers ──────────────────────────────────────────────────

def _confirm_and_log(action, details, dry_run=False, yes=False):
    if dry_run:
        click.secho(f"  DRY RUN: {action} — {details}", fg="yellow")
        return False
    if not yes:
        click.confirm(f"  Execute: {action}?", abort=True)
    return True

def _auto_log(action, details, campaign_name="", campaign_id=""):
    try:
        import json as _json
        conn = get_db()
        ts = now_local()
        raw = {"timestamp": ts, "action": action, "details": details, "campaign": campaign_name, "campaign_id": campaign_id, "agent": "gads-cli"}
        conn.execute(
            "INSERT INTO changelog (timestamp, action, campaign, campaign_id, details, reason, agent, snapshot_ref, script, raw_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (ts, action, campaign_name, campaign_id, details, "", "gads-cli", "", "", _json.dumps(raw)))
        conn.commit()
        conn.close()
    except Exception:
        pass


# ── Campaign commands ────────────────────────────────────────

@campaign.command("list")
@click.option("--json", "as_json", is_flag=True)
def campaign_list(as_json):
    """List all campaigns with status and budget."""
    creds = get_credentials()
    results = run_gaql(creds, """
        SELECT campaign.name, campaign.id, campaign.status,
               campaign.advertising_channel_type, campaign_budget.amount_micros,
               campaign.bidding_strategy_type
        FROM campaign WHERE campaign.status != 'REMOVED' ORDER BY campaign.name""")
    if as_json:
        return print_json(results)
    rows = []
    for r in results:
        c, b = r.get("campaign", {}), r.get("campaignBudget", {})
        rows.append({"name": c.get("name",""), "id": c.get("id",""), "status": c.get("status",""),
                     "type": c.get("advertisingChannelType",""),
                     "budget": round(int(b.get("amountMicros",0))/1e6, 2),
                     "bidding": c.get("biddingStrategyType","")})
    print_table(rows, ["name", "id", "status", "type", "budget", "bidding"])

@campaign.command("status")
@click.argument("campaign_id")
@click.argument("status", type=click.Choice(["ENABLED", "PAUSED"], case_sensitive=False))
@click.option("--dry-run", is_flag=True)
@click.option("--yes", "-y", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
def campaign_status_cmd(campaign_id, status, dry_run, yes, as_json):
    """Enable or pause a campaign."""
    enforce_allowed_caller()
    status = status.upper()
    op = {"update": {"resourceName": f"customers/{CUSTOMER_ID}/campaigns/{campaign_id}", "status": status}, "updateMask": "status"}
    if not _confirm_and_log(f"campaign {campaign_id} → {status}", f"status change", dry_run, yes):
        return
    result = ads_mutate(get_credentials(), "campaigns", [op])
    _auto_log("campaign_status", f"{campaign_id} → {status}", campaign_id=campaign_id)
    if as_json:
        return print_json(result)
    click.secho(f"✓ Campaign {campaign_id} → {status}", fg="green")

@campaign.command("budget")
@click.argument("campaign_id")
@click.argument("amount", type=float)
@click.option("--dry-run", is_flag=True)
@click.option("--yes", "-y", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
def campaign_budget_cmd(campaign_id, amount, dry_run, yes, as_json):
    """Change campaign daily budget."""
    enforce_allowed_caller()
    creds = get_credentials()
    # Lookup budget resource name
    results = run_gaql(creds, f"SELECT campaign.id, campaign_budget.resource_name FROM campaign WHERE campaign.id = {campaign_id}")
    if not results:
        click.secho(f"✗ Campaign {campaign_id} not found", fg="red", err=True)
        raise SystemExit(1)
    budget_rn = results[0].get("campaignBudget", {}).get("resourceName", "")
    if not budget_rn:
        click.secho("✗ No budget resource found", fg="red", err=True)
        raise SystemExit(1)
    micros = str(int(amount * 1_000_000))
    op = {"update": {"resourceName": budget_rn, "amountMicros": micros}, "updateMask": "amountMicros"}
    if not _confirm_and_log(f"budget → {amount} {CURRENCY}", f"campaign {campaign_id}", dry_run, yes):
        return
    result = ads_mutate(creds, "campaignBudgets", [op])
    _auto_log("campaign_budget", f"{campaign_id} budget → {amount} {CURRENCY}", campaign_id=campaign_id)
    if as_json:
        return print_json(result)
    click.secho(f"✓ Campaign {campaign_id} budget → {amount} {CURRENCY}", fg="green")

@campaign.command("perf")
@click.option("--days", "-d", type=int, default=7)
@click.option("--json", "as_json", is_flag=True)
def campaign_perf(days, as_json):
    """Campaign performance from API (last N days)."""
    from datetime import datetime, timedelta
    d_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    d_to = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    results = run_gaql(get_credentials(), f"""
        SELECT campaign.name, campaign.id, metrics.impressions, metrics.clicks,
               metrics.conversions, metrics.cost_micros, metrics.ctr,
               metrics.conversions_from_interactions_rate
        FROM campaign WHERE segments.date BETWEEN '{d_from}' AND '{d_to}'
          AND campaign.status != 'REMOVED'
        ORDER BY metrics.conversions DESC""")
    if as_json:
        return print_json(results)
    rows = []
    for r in results:
        c, m = r.get("campaign", {}), r.get("metrics", {})
        conv = float(m.get("conversions", 0))
        cost = int(m.get("costMicros", 0)) / 1e6
        rows.append({"name": c.get("name",""), "impr": m.get("impressions",0),
                     "clicks": m.get("clicks",0), "conv": conv,
                     "cost": round(cost, 2),
                     "cpa": round(cost/conv, 2) if conv > 0 else "—",
                     "ctr": m.get("ctr",""), "cvr": m.get("conversionsFromInteractionsRate","")})
    print_table(rows, ["name", "impr", "clicks", "conv", "cost", "cpa", "ctr", "cvr"])


# ── Ad Group commands ────────────────────────────────────────

@adgroup.command("list")
@click.option("--campaign", "-c", "campaign_id", required=True)
@click.option("--json", "as_json", is_flag=True)
def adgroup_list(campaign_id, as_json):
    """List ad groups in a campaign."""
    results = run_gaql(get_credentials(), f"""
        SELECT ad_group.name, ad_group.id, ad_group.status, ad_group.type
        FROM ad_group WHERE campaign.id = {campaign_id} ORDER BY ad_group.name""")
    if as_json:
        return print_json(results)
    rows = [{"name": r.get("adGroup",{}).get("name",""), "id": r.get("adGroup",{}).get("id",""),
             "status": r.get("adGroup",{}).get("status",""), "type": r.get("adGroup",{}).get("type","")}
            for r in results]
    print_table(rows, ["name", "id", "status", "type"])

@adgroup.command("status")
@click.argument("adgroup_id")
@click.argument("status", type=click.Choice(["ENABLED", "PAUSED"], case_sensitive=False))
@click.option("--dry-run", is_flag=True)
@click.option("--yes", "-y", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
def adgroup_status_cmd(adgroup_id, status, dry_run, yes, as_json):
    """Enable or pause an ad group."""
    enforce_allowed_caller()
    status = status.upper()
    op = {"update": {"resourceName": f"customers/{CUSTOMER_ID}/adGroups/{adgroup_id}", "status": status}, "updateMask": "status"}
    if not _confirm_and_log(f"ad group {adgroup_id} → {status}", "status change", dry_run, yes):
        return
    result = ads_mutate(get_credentials(), "adGroups", [op])
    _auto_log("adgroup_status", f"{adgroup_id} → {status}")
    if as_json:
        return print_json(result)
    click.secho(f"✓ Ad group {adgroup_id} → {status}", fg="green")

@adgroup.command("create")
@click.argument("campaign_id")
@click.argument("name")
@click.option("--dry-run", is_flag=True)
@click.option("--yes", "-y", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
def adgroup_create_cmd(campaign_id, name, dry_run, yes, as_json):
    """Create an ad group."""
    enforce_allowed_caller()
    op = {"create": {"campaign": f"customers/{CUSTOMER_ID}/campaigns/{campaign_id}", "name": name, "status": "ENABLED"}}
    if not _confirm_and_log(f"create ad group '{name}' in campaign {campaign_id}", "create", dry_run, yes):
        return
    result = ads_mutate(get_credentials(), "adGroups", [op])
    _auto_log("adgroup_create", f"'{name}' in campaign {campaign_id}", campaign_id=campaign_id)
    if as_json:
        return print_json(result)
    click.secho(f"✓ Created ad group '{name}'", fg="green")


# ── Ad commands ──────────────────────────────────────────────

@ad_group.command("list")
@click.option("--campaign", "-c", "campaign_id", default=None)
@click.option("--adgroup", "-a", "adgroup_id", default=None)
@click.option("--json", "as_json", is_flag=True)
def ad_list(campaign_id, adgroup_id, as_json):
    """List ads with creatives."""
    where = "WHERE ad_group_ad.status != 'REMOVED'"
    if campaign_id:
        where += f" AND campaign.id = {campaign_id}"
    if adgroup_id:
        where += f" AND ad_group.id = {adgroup_id}"
    results = run_gaql(get_credentials(), f"""
        SELECT ad_group.name, ad_group_ad.ad.id, ad_group_ad.status,
               ad_group_ad.ad.type, ad_group_ad.ad.responsive_search_ad.headlines,
               ad_group_ad.ad.responsive_search_ad.descriptions
        FROM ad_group_ad {where} ORDER BY ad_group.name""")
    if as_json:
        return print_json(results)
    rows = []
    for r in results:
        ag = r.get("adGroup", {})
        aga = r.get("adGroupAd", {})
        ad = aga.get("ad", {})
        rows.append({"ad_group": ag.get("name",""), "ad_id": ad.get("id",""),
                     "status": aga.get("status",""), "type": ad.get("type","")})
    print_table(rows, ["ad_group", "ad_id", "status", "type"])

@ad_group.command("status")
@click.argument("adgroup_id")
@click.argument("ad_id")
@click.argument("status", type=click.Choice(["ENABLED", "PAUSED"], case_sensitive=False))
@click.option("--dry-run", is_flag=True)
@click.option("--yes", "-y", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
def ad_status_cmd(adgroup_id, ad_id, status, dry_run, yes, as_json):
    """Enable or pause an ad."""
    enforce_allowed_caller()
    status = status.upper()
    op = {"update": {"resourceName": f"customers/{CUSTOMER_ID}/adGroupAds/{adgroup_id}~{ad_id}", "status": status}, "updateMask": "status"}
    if not _confirm_and_log(f"ad {ad_id} → {status}", "status change", dry_run, yes):
        return
    result = ads_mutate(get_credentials(), "adGroupAds", [op])
    _auto_log("ad_status", f"ad {ad_id} in adgroup {adgroup_id} → {status}")
    if as_json:
        return print_json(result)
    click.secho(f"✓ Ad {ad_id} → {status}", fg="green")

@ad_group.command("perf")
@click.option("--days", "-d", type=int, default=7)
@click.option("--campaign", "-c", "campaign_id", default=None)
@click.option("--json", "as_json", is_flag=True)
def ad_perf(days, campaign_id, as_json):
    """Ad-level performance."""
    from datetime import datetime, timedelta
    d_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    d_to = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    where = f"WHERE segments.date BETWEEN '{d_from}' AND '{d_to}' AND ad_group_ad.status != 'REMOVED'"
    if campaign_id:
        where += f" AND campaign.id = {campaign_id}"
    results = run_gaql(get_credentials(), f"""
        SELECT ad_group.name, ad_group_ad.ad.id, ad_group_ad.ad.type,
               metrics.impressions, metrics.clicks, metrics.conversions, metrics.cost_micros
        FROM ad_group_ad {where} ORDER BY metrics.conversions DESC""")
    if as_json:
        return print_json(results)
    rows = []
    for r in results:
        ag, aga, m = r.get("adGroup",{}), r.get("adGroupAd",{}).get("ad",{}), r.get("metrics",{})
        conv = float(m.get("conversions",0))
        cost = int(m.get("costMicros",0))/1e6
        rows.append({"ad_group": ag.get("name",""), "ad_id": aga.get("id",""), "type": aga.get("type",""),
                     "impr": m.get("impressions",0), "clicks": m.get("clicks",0), "conv": conv,
                     "cost": round(cost,2), "cpa": round(cost/conv,2) if conv>0 else "—"})
    print_table(rows, ["ad_group", "ad_id", "type", "impr", "clicks", "conv", "cost", "cpa"])


# ── Keyword commands ─────────────────────────────────────────

@keyword.command("list")
@click.option("--campaign", "-c", "campaign_id", required=True)
@click.option("--days", "-d", type=int, default=30)
@click.option("--json", "as_json", is_flag=True)
def keyword_list(campaign_id, days, as_json):
    """List keywords with performance."""
    from datetime import datetime, timedelta
    d_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    d_to = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    results = run_gaql(get_credentials(), f"""
        SELECT ad_group.name, ad_group_criterion.keyword.text,
               ad_group_criterion.keyword.match_type, ad_group_criterion.criterion_id,
               metrics.impressions, metrics.clicks, metrics.conversions, metrics.cost_micros
        FROM keyword_view WHERE campaign.id = {campaign_id}
          AND segments.date BETWEEN '{d_from}' AND '{d_to}'
        ORDER BY metrics.clicks DESC""")
    if as_json:
        return print_json(results)
    rows = []
    for r in results:
        ag, kw, m = r.get("adGroup",{}), r.get("adGroupCriterion",{}).get("keyword",{}), r.get("metrics",{})
        conv = float(m.get("conversions",0))
        cost = int(m.get("costMicros",0))/1e6
        rows.append({"ad_group": ag.get("name",""), "keyword": kw.get("text",""),
                     "match": kw.get("matchType",""), "impr": m.get("impressions",0),
                     "clicks": m.get("clicks",0), "conv": conv, "cost": round(cost,2),
                     "cpa": round(cost/conv,2) if conv>0 else "—"})
    print_table(rows, ["ad_group", "keyword", "match", "impr", "clicks", "conv", "cost", "cpa"])

@keyword.command("add")
@click.argument("adgroup_id")
@click.argument("text")
@click.option("--match-type", "-m", type=click.Choice(["EXACT", "PHRASE", "BROAD"], case_sensitive=False), default="PHRASE")
@click.option("--dry-run", is_flag=True)
@click.option("--yes", "-y", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
def keyword_add(adgroup_id, text, match_type, dry_run, yes, as_json):
    """Add a keyword to an ad group."""
    enforce_allowed_caller()
    op = {"create": {"adGroup": f"customers/{CUSTOMER_ID}/adGroups/{adgroup_id}",
                     "keyword": {"text": text, "matchType": match_type.upper()}, "status": "ENABLED"}}
    if not _confirm_and_log(f"add keyword '{text}' [{match_type}] to adgroup {adgroup_id}", "add keyword", dry_run, yes):
        return
    result = ads_mutate(get_credentials(), "adGroupCriteria", [op])
    _auto_log("keyword_add", f"'{text}' [{match_type}] → adgroup {adgroup_id}")
    if as_json:
        return print_json(result)
    click.secho(f"✓ Added keyword '{text}' [{match_type}]", fg="green")

@keyword.command("remove")
@click.argument("adgroup_id")
@click.argument("criterion_id")
@click.option("--dry-run", is_flag=True)
@click.option("--yes", "-y", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
def keyword_remove(adgroup_id, criterion_id, dry_run, yes, as_json):
    """Remove a keyword from an ad group."""
    enforce_allowed_caller()
    # Tilde format for ad group criteria
    rn = f"customers/{CUSTOMER_ID}/adGroupCriteria/{adgroup_id}~{criterion_id}"
    op = {"remove": rn}
    if not _confirm_and_log(f"remove criterion {criterion_id} from adgroup {adgroup_id}", "remove keyword", dry_run, yes):
        return
    result = ads_mutate(get_credentials(), "adGroupCriteria", [op])
    _auto_log("keyword_remove", f"criterion {criterion_id} from adgroup {adgroup_id}")
    if as_json:
        return print_json(result)
    click.secho(f"✓ Removed criterion {criterion_id}", fg="green")

@keyword.command("negative")
@click.argument("campaign_id")
@click.argument("text")
@click.option("--match-type", "-m", type=click.Choice(["EXACT", "PHRASE", "BROAD"], case_sensitive=False), default="PHRASE")
@click.option("--dry-run", is_flag=True)
@click.option("--yes", "-y", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
def keyword_negative(campaign_id, text, match_type, dry_run, yes, as_json):
    """Add a negative keyword to a campaign."""
    enforce_allowed_caller()
    op = {"create": {"campaign": f"customers/{CUSTOMER_ID}/campaigns/{campaign_id}",
                     "keyword": {"text": text, "matchType": match_type.upper()}, "negative": True}}
    if not _confirm_and_log(f"add negative '{text}' [{match_type}] to campaign {campaign_id}", "add negative", dry_run, yes):
        return
    result = ads_mutate(get_credentials(), "campaignCriteria", [op])
    _auto_log("keyword_negative", f"negative '{text}' [{match_type}] → campaign {campaign_id}", campaign_id=campaign_id)
    if as_json:
        return print_json(result)
    click.secho(f"✓ Added negative '{text}' [{match_type}]", fg="green")

@keyword.command("search-terms")
@click.option("--days", "-d", type=int, default=7)
@click.option("--campaign", "-c", "campaign_id", default=None)
@click.option("--min-clicks", type=int, default=0)
@click.option("--json", "as_json", is_flag=True)
def keyword_search_terms(days, campaign_id, min_clicks, as_json):
    """Search terms report."""
    from datetime import datetime, timedelta
    d_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    d_to = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    where = f"WHERE segments.date BETWEEN '{d_from}' AND '{d_to}'"
    if campaign_id:
        where += f" AND campaign.id = {campaign_id}"
    if min_clicks > 0:
        where += f" AND metrics.clicks >= {min_clicks}"
    results = run_gaql(get_credentials(), f"""
        SELECT search_term_view.search_term, campaign.name,
               metrics.impressions, metrics.clicks, metrics.conversions, metrics.cost_micros
        FROM search_term_view {where} ORDER BY metrics.clicks DESC""")
    if as_json:
        return print_json(results)
    rows = []
    for r in results:
        st, c, m = r.get("searchTermView",{}), r.get("campaign",{}), r.get("metrics",{})
        conv = float(m.get("conversions",0))
        cost = int(m.get("costMicros",0))/1e6
        rows.append({"search_term": st.get("searchTerm",""), "campaign": c.get("name",""),
                     "impr": m.get("impressions",0), "clicks": m.get("clicks",0),
                     "conv": conv, "cost": round(cost,2),
                     "cpa": round(cost/conv,2) if conv>0 else "—"})
    print_table(rows, ["search_term", "campaign", "impr", "clicks", "conv", "cost", "cpa"])

@keyword.command("ideas")
@click.option("--keywords", "-k", default=None, help="Comma-separated seed keywords.")
@click.option("--url", "-u", default=None, help="Seed URL for ideas.")
@click.option("--language", default="1000", help="Language ID (default: 1000=English).")
@click.option("--geo", default=None, help="Comma-separated geo target IDs (e.g. 2784=UAE).")
@click.option("--json", "as_json", is_flag=True)
def keyword_ideas_cmd(keywords, url, language, geo, as_json):
    """Generate keyword ideas (requires Standard Access dev token)."""
    kw_list = [k.strip() for k in keywords.split(",")] if keywords else None
    geo_list = [g.strip() for g in geo.split(",")] if geo else None
    result = generate_keyword_ideas(get_credentials(), keywords=kw_list, url=url, language_id=language, geo_ids=geo_list)
    if as_json:
        return print_json(result)
    ideas = result.get("results", [])
    rows = []
    for idea in ideas[:50]:
        kw = idea.get("keywordIdeaMetrics", {})
        rows.append({"keyword": idea.get("text",""),
                     "avg_monthly": kw.get("avgMonthlySearches",""),
                     "competition": kw.get("competition",""),
                     "low_cpc": kw.get("lowTopOfPageBidMicros",""),
                     "high_cpc": kw.get("highTopOfPageBidMicros","")})
    print_table(rows, ["keyword", "avg_monthly", "competition", "low_cpc", "high_cpc"])
    click.echo(f"\n  {len(ideas)} idea(s)")

@keyword.command("forecast")
@click.option("--keywords", "-k", required=True, help="Comma-separated keywords.")
@click.option("--language", default="1000")
@click.option("--geo", default=None, help="Comma-separated geo target IDs.")
@click.option("--json", "as_json", is_flag=True)
def keyword_forecast_cmd(keywords, language, geo, as_json):
    """Keyword traffic/cost forecast (requires Standard Access dev token)."""
    kw_list = [k.strip() for k in keywords.split(",")]
    geo_list = [g.strip() for g in geo.split(",")] if geo else None
    result = generate_keyword_forecast(get_credentials(), keywords=kw_list, language_id=language, geo_ids=geo_list)
    if as_json:
        return print_json(result)
    print_json(result)


# ── Asset commands ───────────────────────────────────────────

@asset_group.command("list")
@click.option("--type", "asset_type", default=None, help="Filter by type (IMAGE, SITELINK, etc).")
@click.option("--json", "as_json", is_flag=True)
def asset_list(asset_type, as_json):
    """List assets."""
    where = "WHERE asset.type != 'UNSPECIFIED'"
    if asset_type:
        where += f" AND asset.type = '{asset_type.upper()}'"
    results = run_gaql(get_credentials(), f"""
        SELECT asset.id, asset.name, asset.type, asset.resource_name
        FROM asset {where} ORDER BY asset.type, asset.name""")
    if as_json:
        return print_json(results)
    rows = [{"id": r.get("asset",{}).get("id",""), "name": r.get("asset",{}).get("name",""),
             "type": r.get("asset",{}).get("type","")} for r in results]
    print_table(rows, ["id", "name", "type"])

@asset_group.command("sitelink")
@click.argument("campaign_id")
@click.option("--link-text", required=True)
@click.option("--desc1", default="")
@click.option("--desc2", default="")
@click.option("--url", required=True)
@click.option("--dry-run", is_flag=True)
@click.option("--yes", "-y", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
def asset_sitelink(campaign_id, link_text, desc1, desc2, url, dry_run, yes, as_json):
    """Add a sitelink to a campaign (two-step: create asset + link)."""
    enforce_allowed_caller()
    if not _confirm_and_log(f"add sitelink '{link_text}' → {url} to campaign {campaign_id}", "sitelink", dry_run, yes):
        return
    creds = get_credentials()
    # Step 1: Create the sitelink asset — finalUrls at top level, NOT inside sitelinkAsset
    asset_op = {"create": {"sitelinkAsset": {"linkText": link_text, "description1": desc1, "description2": desc2}, "finalUrls": [url]}}
    asset_result = ads_mutate(creds, "assets", [asset_op])
    asset_rn = asset_result.get("results", [{}])[0].get("resourceName", "")
    if not asset_rn:
        click.secho("✗ Failed to create sitelink asset", fg="red", err=True)
        raise SystemExit(1)
    # Step 2: Link to campaign
    link_op = {"create": {"asset": asset_rn, "campaign": f"customers/{CUSTOMER_ID}/campaigns/{campaign_id}", "fieldType": "SITELINK"}}
    result = ads_mutate(creds, "campaignAssets", [link_op])
    _auto_log("asset_sitelink", f"'{link_text}' → campaign {campaign_id}", campaign_id=campaign_id)
    if as_json:
        return print_json(result)
    click.secho(f"✓ Sitelink '{link_text}' added to campaign {campaign_id}", fg="green")

@asset_group.command("callout")
@click.argument("campaign_id")
@click.option("--text", required=True)
@click.option("--dry-run", is_flag=True)
@click.option("--yes", "-y", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
def asset_callout(campaign_id, text, dry_run, yes, as_json):
    """Add a callout extension to a campaign."""
    enforce_allowed_caller()
    if not _confirm_and_log(f"add callout '{text}' to campaign {campaign_id}", "callout", dry_run, yes):
        return
    creds = get_credentials()
    asset_op = {"create": {"calloutAsset": {"calloutText": text}}}
    asset_result = ads_mutate(creds, "assets", [asset_op])
    asset_rn = asset_result.get("results", [{}])[0].get("resourceName", "")
    link_op = {"create": {"asset": asset_rn, "campaign": f"customers/{CUSTOMER_ID}/campaigns/{campaign_id}", "fieldType": "CALLOUT"}}
    result = ads_mutate(creds, "campaignAssets", [link_op])
    _auto_log("asset_callout", f"'{text}' → campaign {campaign_id}", campaign_id=campaign_id)
    if as_json:
        return print_json(result)
    click.secho(f"✓ Callout '{text}' added", fg="green")

@asset_group.command("call")
@click.argument("campaign_id")
@click.option("--phone", required=True)
@click.option("--country-code", default="US")
@click.option("--dry-run", is_flag=True)
@click.option("--yes", "-y", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
def asset_call(campaign_id, phone, country_code, dry_run, yes, as_json):
    """Add a call extension to a campaign."""
    enforce_allowed_caller()
    if not _confirm_and_log(f"add call {phone} ({country_code}) to campaign {campaign_id}", "call ext", dry_run, yes):
        return
    creds = get_credentials()
    asset_op = {"create": {"callAsset": {"phoneNumber": phone, "countryCode": country_code.upper()}}}
    asset_result = ads_mutate(creds, "assets", [asset_op])
    asset_rn = asset_result.get("results", [{}])[0].get("resourceName", "")
    link_op = {"create": {"asset": asset_rn, "campaign": f"customers/{CUSTOMER_ID}/campaigns/{campaign_id}", "fieldType": "CALL"}}
    result = ads_mutate(creds, "campaignAssets", [link_op])
    _auto_log("asset_call", f"{phone} ({country_code}) → campaign {campaign_id}", campaign_id=campaign_id)
    if as_json:
        return print_json(result)
    click.secho(f"✓ Call extension {phone} added", fg="green")


# ── Conversion commands ──────────────────────────────────────

@conversion_group.command("list")
@click.option("--json", "as_json", is_flag=True)
def conversion_list(as_json):
    """List conversion actions."""
    results = run_gaql(get_credentials(), """
        SELECT conversion_action.name, conversion_action.id, conversion_action.type,
               conversion_action.status, conversion_action.category
        FROM conversion_action ORDER BY conversion_action.name""")
    if as_json:
        return print_json(results)
    rows = [{"name": r.get("conversionAction",{}).get("name",""),
             "id": r.get("conversionAction",{}).get("id",""),
             "type": r.get("conversionAction",{}).get("type",""),
             "status": r.get("conversionAction",{}).get("status",""),
             "category": r.get("conversionAction",{}).get("category","")}
            for r in results]
    print_table(rows, ["name", "id", "type", "status", "category"])

@conversion_group.command("create")
@click.argument("name")
@click.option("--type", "conv_type", default="WEBPAGE", type=click.Choice(["WEBPAGE", "UPLOAD", "AD_CALL", "CLICK_TO_CALL"]))
@click.option("--category", default="DEFAULT")
@click.option("--dry-run", is_flag=True)
@click.option("--yes", "-y", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
def conversion_create(name, conv_type, category, dry_run, yes, as_json):
    """Create a conversion action."""
    enforce_allowed_caller()
    op = {"create": {"name": name, "type": conv_type, "category": category, "status": "ENABLED"}}
    if not _confirm_and_log(f"create conversion action '{name}' [{conv_type}]", "create conversion", dry_run, yes):
        return
    result = ads_mutate(get_credentials(), "conversionActions", [op])
    _auto_log("conversion_create", f"'{name}' [{conv_type}]")
    if as_json:
        return print_json(result)
    click.secho(f"✓ Created conversion action '{name}'", fg="green")

@conversion_group.command("tag")
@click.argument("conversion_id")
@click.option("--json", "as_json", is_flag=True)
def conversion_tag(conversion_id, as_json):
    """Get conversion tracking tag/snippet."""
    results = run_gaql(get_credentials(), f"""
        SELECT conversion_action.name, conversion_action.id,
               conversion_action.tag_snippets
        FROM conversion_action WHERE conversion_action.id = {conversion_id}""")
    if as_json:
        return print_json(results)
    if results:
        ca = results[0].get("conversionAction", {})
        click.secho(f"\n  {ca.get('name', '')} (ID: {ca.get('id', '')})\n", bold=True)
        snippets = ca.get("tagSnippets", [])
        for s in snippets:
            click.secho(f"  Type: {s.get('type','')}", fg="cyan")
            click.echo(f"  {s.get('eventSnippet','')}\n")
    else:
        click.echo("  (not found)")

@conversion_group.command("perf")
@click.option("--days", "-d", type=int, default=7)
@click.option("--json", "as_json", is_flag=True)
def conversion_perf(days, as_json):
    """Conversion performance by action."""
    from datetime import datetime, timedelta
    d_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    d_to = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    results = run_gaql(get_credentials(), f"""
        SELECT segments.conversion_action_name, metrics.conversions,
               metrics.all_conversions, metrics.conversions_value
        FROM campaign WHERE segments.date BETWEEN '{d_from}' AND '{d_to}'
          AND metrics.conversions > 0
        ORDER BY metrics.conversions DESC""")
    if as_json:
        return print_json(results)
    # Aggregate by conversion action
    agg = {}
    for r in results:
        name = r.get("segments",{}).get("conversionActionName","")
        m = r.get("metrics",{})
        if name not in agg:
            agg[name] = {"name": name, "conv": 0, "all_conv": 0, "value": 0}
        agg[name]["conv"] += float(m.get("conversions",0))
        agg[name]["all_conv"] += float(m.get("allConversions",0))
        agg[name]["value"] += float(m.get("conversionsValue",0))
    rows = sorted(agg.values(), key=lambda x: x["conv"], reverse=True)
    print_table(rows, ["name", "conv", "all_conv", "value"])

@conversion_group.command("upload")
@click.option("--gclid", required=True)
@click.option("--action-id", required=True, help="Conversion action resource name.")
@click.option("--time", "conv_time", required=True, help="Conversion time (ISO 8601).")
@click.option("--value", type=float, default=None)
@click.option("--currency", default=None)
@click.option("--dry-run", is_flag=True)
@click.option("--yes", "-y", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
def conversion_upload_cmd(gclid, action_id, conv_time, value, currency, dry_run, yes, as_json):
    """Upload an offline conversion."""
    enforce_allowed_caller()
    conv = {"gclid": gclid, "conversionDateTime": conv_time}
    if value is not None:
        conv["conversionValue"] = value
    if currency:
        conv["currencyCode"] = currency
    if not _confirm_and_log(f"upload conversion gclid={gclid}", "upload conversion", dry_run, yes):
        return
    result = ads_upload_click_conversions(get_credentials(), [conv], action_id)
    _auto_log("conversion_upload", f"gclid={gclid}")
    if as_json:
        return print_json(result)
    click.secho("✓ Conversion uploaded", fg="green")


# ── Audience commands ────────────────────────────────────────

@audience_group.command("list")
@click.option("--json", "as_json", is_flag=True)
def audience_list(as_json):
    """List user lists / audiences."""
    results = run_gaql(get_credentials(), """
        SELECT user_list.name, user_list.id, user_list.type,
               user_list.size_for_search, user_list.size_for_display,
               user_list.membership_status, user_list.match_rate_percentage
        FROM user_list ORDER BY user_list.name""")
    if as_json:
        return print_json(results)
    rows = [{"name": r.get("userList",{}).get("name",""),
             "id": r.get("userList",{}).get("id",""),
             "type": r.get("userList",{}).get("type",""),
             "search_size": r.get("userList",{}).get("sizeForSearch",""),
             "display_size": r.get("userList",{}).get("sizeForDisplay",""),
             "match_rate": r.get("userList",{}).get("matchRatePercentage","")}
            for r in results]
    print_table(rows, ["name", "id", "type", "search_size", "display_size", "match_rate"])


# ── Report commands ──────────────────────────────────────────

@report_group.command("geo")
@click.option("--days", "-d", type=int, default=7)
@click.option("--json", "as_json", is_flag=True)
def report_geo(days, as_json):
    """Geographic performance report."""
    from datetime import datetime, timedelta
    d_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    d_to = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    results = run_gaql(get_credentials(), f"""
        SELECT geographic_view.country_criterion_id, geographic_view.location_type,
               metrics.impressions, metrics.clicks, metrics.conversions, metrics.cost_micros
        FROM geographic_view WHERE segments.date BETWEEN '{d_from}' AND '{d_to}'
        ORDER BY metrics.clicks DESC""")
    if as_json:
        return print_json(results)
    rows = []
    for r in results:
        gv, m = r.get("geographicView",{}), r.get("metrics",{})
        conv = float(m.get("conversions",0))
        cost = int(m.get("costMicros",0))/1e6
        rows.append({"country_id": gv.get("countryCriterionId",""), "type": gv.get("locationType",""),
                     "impr": m.get("impressions",0), "clicks": m.get("clicks",0),
                     "conv": conv, "cost": round(cost,2)})
    print_table(rows, ["country_id", "type", "impr", "clicks", "conv", "cost"])

@report_group.command("hourly")
@click.option("--days", "-d", type=int, default=7)
@click.option("--json", "as_json", is_flag=True)
def report_hourly(days, as_json):
    """Hourly performance breakdown."""
    from datetime import datetime, timedelta
    d_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    d_to = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    results = run_gaql(get_credentials(), f"""
        SELECT segments.hour, metrics.impressions, metrics.clicks,
               metrics.conversions, metrics.cost_micros
        FROM campaign WHERE segments.date BETWEEN '{d_from}' AND '{d_to}'
        ORDER BY segments.hour""")
    if as_json:
        return print_json(results)
    # Aggregate by hour
    hours = {}
    for r in results:
        h = r.get("segments",{}).get("hour","")
        m = r.get("metrics",{})
        if h not in hours:
            hours[h] = {"hour": h, "impr": 0, "clicks": 0, "conv": 0, "cost": 0}
        hours[h]["impr"] += int(m.get("impressions",0))
        hours[h]["clicks"] += int(m.get("clicks",0))
        hours[h]["conv"] += float(m.get("conversions",0))
        hours[h]["cost"] += int(m.get("costMicros",0))/1e6
    rows = [{"hour": v["hour"], "impr": v["impr"], "clicks": v["clicks"],
             "conv": round(v["conv"],1), "cost": round(v["cost"],2)} for v in sorted(hours.values(), key=lambda x: int(x["hour"]))]
    print_table(rows, ["hour", "impr", "clicks", "conv", "cost"])

@report_group.command("devices")
@click.option("--days", "-d", type=int, default=7)
@click.option("--json", "as_json", is_flag=True)
def report_devices(days, as_json):
    """Device performance breakdown."""
    from datetime import datetime, timedelta
    d_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    d_to = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    results = run_gaql(get_credentials(), f"""
        SELECT segments.device, metrics.impressions, metrics.clicks,
               metrics.conversions, metrics.cost_micros
        FROM campaign WHERE segments.date BETWEEN '{d_from}' AND '{d_to}'
        ORDER BY metrics.clicks DESC""")
    if as_json:
        return print_json(results)
    devs = {}
    for r in results:
        d = r.get("segments",{}).get("device","")
        m = r.get("metrics",{})
        if d not in devs:
            devs[d] = {"device": d, "impr": 0, "clicks": 0, "conv": 0, "cost": 0}
        devs[d]["impr"] += int(m.get("impressions",0))
        devs[d]["clicks"] += int(m.get("clicks",0))
        devs[d]["conv"] += float(m.get("conversions",0))
        devs[d]["cost"] += int(m.get("costMicros",0))/1e6
    rows = [{"device": v["device"], "impr": v["impr"], "clicks": v["clicks"],
             "conv": round(v["conv"],1), "cost": round(v["cost"],2)} for v in sorted(devs.values(), key=lambda x: x["clicks"], reverse=True)]
    print_table(rows, ["device", "impr", "clicks", "conv", "cost"])

@report_group.command("search-terms")
@click.option("--days", "-d", type=int, default=7)
@click.option("--campaign", "-c", "campaign_id", default=None)
@click.option("--min-clicks", type=int, default=0)
@click.option("--json", "as_json", is_flag=True)
def report_search_terms(days, campaign_id, min_clicks, as_json):
    """Search terms report (alias for keyword search-terms)."""
    # Delegate to keyword search-terms
    ctx = click.get_current_context()
    ctx.invoke(keyword_search_terms, days=days, campaign_id=campaign_id, min_clicks=min_clicks, as_json=as_json)


# ── Generic mutate commands (escape hatch) ───────────────────

@cli.command("mutate")
@click.argument("resource_type")
@click.argument("operations_json")
@click.option("--dry-run", is_flag=True)
@click.option("--yes", "-y", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
def mutate_single(resource_type, operations_json, dry_run, yes, as_json):
    """Generic single-resource mutate (escape hatch)."""
    enforce_allowed_caller()
    import json as _json
    try:
        ops = _json.loads(operations_json)
    except _json.JSONDecodeError as e:
        click.secho(f"✗ Invalid JSON: {e}", fg="red", err=True)
        raise SystemExit(1)
    if not isinstance(ops, list):
        ops = [ops]
    if not _confirm_and_log(f"mutate {resource_type} ({len(ops)} ops)", f"generic mutate", dry_run, yes):
        return
    result = ads_mutate(get_credentials(), resource_type, ops)
    _auto_log("mutate", f"{resource_type}: {len(ops)} operations")
    if as_json:
        return print_json(result)
    click.secho(f"✓ Mutated {resource_type}", fg="green")
    print_json(result)

@cli.command("batch-mutate")
@click.argument("operations_json")
@click.option("--dry-run", is_flag=True)
@click.option("--yes", "-y", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
def batch_mutate_cmd(operations_json, dry_run, yes, as_json):
    """Generic cross-resource batch mutate (escape hatch)."""
    enforce_allowed_caller()
    import json as _json
    try:
        ops = _json.loads(operations_json)
    except _json.JSONDecodeError as e:
        click.secho(f"✗ Invalid JSON: {e}", fg="red", err=True)
        raise SystemExit(1)
    if not isinstance(ops, list):
        ops = [ops]
    if not _confirm_and_log(f"batch mutate ({len(ops)} ops)", f"batch mutate", dry_run, yes):
        return
    result = ads_batch_mutate(get_credentials(), ops)
    _auto_log("batch_mutate", f"{len(ops)} operations")
    if as_json:
        return print_json(result)
    click.secho(f"✓ Batch mutate complete", fg="green")
    print_json(result)


# ── Standalone commands ──────────────────────────────────────

@cli.command("accounts")
@click.option("--json", "as_json", is_flag=True)
def accounts_cmd(as_json):
    """List accessible Google Ads accounts."""
    results = run_gaql(get_credentials(), """
        SELECT customer_client.id, customer_client.descriptive_name,
               customer_client.status, customer_client.manager
        FROM customer_client ORDER BY customer_client.descriptive_name""")
    if as_json:
        return print_json(results)
    rows = [{"id": r.get("customerClient",{}).get("id",""),
             "name": r.get("customerClient",{}).get("descriptiveName",""),
             "status": r.get("customerClient",{}).get("status",""),
             "manager": r.get("customerClient",{}).get("manager","")}
            for r in results]
    print_table(rows, ["id", "name", "status", "manager"])


# ── Register grouped aliases ────────────────────────────────
ads.add_command(query, name="query")
ads.add_command(perf, name="perf")
ads.add_command(config, name="config")
ads.add_command(refresh, name="refresh")
ads.add_command(snapshot, name="snapshot")
ads.add_command(log, name="log")


def main():
    cli()
