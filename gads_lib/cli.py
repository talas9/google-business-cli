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
    click.secho("  ║   google-business-cli — Setup Wizard     ║", fg="cyan")
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
    click.secho("  Step 2: Google Cloud Project\n", fg="white", bold=True)
    click.echo("  You need a Google Cloud project with APIs enabled.")
    click.echo("  If you don't have one, create it at:")
    click.secho("  → https://console.cloud.google.com/projectcreate\n", fg="blue")
    click.echo("  Then enable these APIs (click each link):")
    apis = [
        ("Google Ads API", "https://console.cloud.google.com/apis/library/googleads.googleapis.com"),
        ("My Business Account Mgmt API", "https://console.cloud.google.com/apis/library/mybusinessaccountmanagement.googleapis.com"),
        ("My Business Business Info API", "https://console.cloud.google.com/apis/library/mybusinessbusinessinformation.googleapis.com"),
        ("Content API for Shopping", "https://console.cloud.google.com/apis/library/content.googleapis.com"),
        ("GA4 Data API", "https://console.cloud.google.com/apis/library/analyticsdata.googleapis.com"),
        ("GA4 Admin API", "https://console.cloud.google.com/apis/library/analyticsadmin.googleapis.com"),
    ]
    for name, url in apis:
        click.echo(f"    • {name}")
        click.secho(f"      {url}", fg="blue")
    click.echo()
    click.pause("  Press Enter when APIs are enabled...")
    click.echo()

    # ── Step 3: OAuth client credentials ─────────────────────
    click.secho("  Step 3: OAuth Client Credentials\n", fg="white", bold=True)
    creds_dir = CREDS_PATH.parent
    client_secret = creds_dir / "client_secret.json"

    if client_secret.exists():
        click.secho("  ✓ client_secret.json found", fg="green")
    else:
        click.echo("  Create OAuth credentials:")
        click.echo("    1. Go to: ")
        click.secho("       https://console.cloud.google.com/apis/credentials", fg="blue")
        click.echo("    2. Click '+ CREATE CREDENTIALS' → 'OAuth client ID'")
        click.echo("    3. Application type: 'Desktop app'")
        click.echo("    4. Name it anything (e.g. 'gads-cli')")
        click.echo("    5. Click 'CREATE', then 'DOWNLOAD JSON'")
        click.echo(f"    6. Save the file as:")
        click.secho(f"       {client_secret}\n", fg="yellow")
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
        click.echo("  Get your developer token:")
        click.echo("    1. Go to: ")
        click.secho("       https://ads.google.com/aw/apicenter", fg="blue")
        click.echo("    2. Copy your developer token")
        click.echo("    3. Add to .env:")
        click.secho("       GOOGLE_ADS_DEVELOPER_TOKEN=your-token-here\n", fg="yellow")
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

    # ── Step 6: Manager account (optional) ───────────────────
    click.secho("  Step 6: Manager Account ID (optional)\n", fg="white", bold=True)
    if LOGIN_CUSTOMER_ID:
        click.secho(f"  ✓ GOOGLE_ADS_LOGIN_CUSTOMER_ID is set", fg="green")
    else:
        click.echo("  If your account is managed by an MCC (manager account),")
        click.echo("  enter the manager's customer ID. Otherwise skip.\n")
        mcc = click.prompt("  Manager customer ID (or Enter to skip)", default="", show_default=False)
        if mcc.strip():
            clean_mcc = mcc.strip().replace("-", "").replace(" ", "")
            _append_env(env_path, "GOOGLE_ADS_LOGIN_CUSTOMER_ID", clean_mcc)
            click.secho("  ✓ Manager ID saved to .env", fg="green")
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

# ── Register grouped aliases ────────────────────────────────
ads.add_command(query, name="query")
ads.add_command(perf, name="perf")
ads.add_command(config, name="config")
ads.add_command(refresh, name="refresh")
ads.add_command(snapshot, name="snapshot")
ads.add_command(log, name="log")


def main():
    cli()
