# google-business-cli

Unified Google platform CLI for managing Google Ads, Google Business Profile, Google Merchant Center, and GA4.

## Quick Start

```bash
cp .env.example .env        # Fill in your credentials
python generate_token.py    # Get OAuth token
./gads doctor               # Verify setup
```

## Commands

```bash
./gads --help               # All commands
./gads doctor               # Readiness check
./gads auth status           # Credential status (never prints secrets)

# Google Ads
./gads query "SELECT campaign.name FROM campaign"
./gads perf --days 7         # Performance from local DB
./gads config                # Campaign configs from API
./gads refresh --days 3      # Pull API data into local DB
./gads snapshot baseline     # Snapshot configs before changes
./gads log "budget_change" "PMax 25→30"  # Append to changelog

# Google Business Profile
./gads gbp accounts
./gads gbp locations --account accounts/123
./gads gbp reviews locations/456

# Merchant Center
./gads merchant status
./gads merchant products --limit 10

# GA4
./gads ga4 report -d date -m activeUsers --start 7daysAgo
./gads ga4 realtime
```

## Configuration

All config via `.env` — see `.env.example`. Required vars:

- `GOOGLE_ADS_DEVELOPER_TOKEN` — from Google Ads API Center
- `GOOGLE_ADS_CUSTOMER_ID` — 10 digits, no dashes
- `GADS_TIMEZONE` — IANA timezone (default: UTC)

## Architecture

- `gads` — main CLI (Click-based, Python 3.10+)
- `gads_lib/` — modular library (config, auth, ads, gbp, merchant, ga4, http, db, output, timeutil)
- `fetch_daily.py` — cron-friendly daily data fetch script
- `generate_token.py` — OAuth token generator (4 scopes)

## Agent Integration

Set `GADS_ENFORCE_CALLER=1` and `GADS_EXPECTED_CALLER=your-agent-name` to restrict CLI access to a specific agent. The calling agent sets `GADS_CALLER_AGENT`.
