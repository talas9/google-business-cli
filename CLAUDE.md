# gads-cli

Unified Google platform CLI for managing Google Ads, Google Business Profile, Google Merchant Center, and GA4.

## Quick Start

```bash
cp .env.example .env        # Fill in your credentials
python generate_token.py    # Get OAuth token (opens browser)
./gads doctor               # Verify setup
```

## Commands

```bash
./gads --help               # All commands
./gads doctor               # Readiness check
./gads auth status          # Credential status (never prints secrets)

# Google Ads
./gads query "SELECT campaign.name FROM campaign"
./gads perf --days 7         # Performance from local DB
./gads config --json         # Campaign configs from API
./gads refresh --days 3      # Pull API data into local DB
./gads snapshot baseline     # Snapshot configs before changes
./gads log "action" "details" # Append to changelog

# Google Business Profile
./gads gbp accounts
./gads gbp locations --account accounts/123
./gads gbp reviews locations/456
./gads gbp reply-review accounts/123/locations/456/reviews/789 "Thank you!"

# Merchant Center
./gads merchant status
./gads merchant products --limit 10
./gads merchant feeds

# GA4
./gads ga4 report -d date -m activeUsers --start 7daysAgo
./gads ga4 realtime
./gads ga4 metadata
```

## Configuration

All configuration via environment variables or `.env` file. See `.env.example` for the full list.

**Required:**
- `GOOGLE_ADS_DEVELOPER_TOKEN` — from Google Ads API Center (Basic Access for most commands; Standard Access needed for Keyword Planner)
- `GOOGLE_ADS_CUSTOMER_ID` — 10 digits, no dashes

**Optional:**
- `GOOGLE_ADS_LOGIN_CUSTOMER_ID` — MCC manager ID
- `GOOGLE_MERCHANT_CENTER_ID` — for Merchant Center commands
- `GOOGLE_GA4_PROPERTY_ID` — for GA4 commands
- `GADS_TIMEZONE` — IANA timezone (default: UTC)

## Architecture

- `gads` — main CLI entry point (Click-based, Python 3.10+)
- `gads_lib/` — modular library:
  - `config.py` — environment-driven configuration, zero hardcoded values
  - `auth.py` — OAuth credential management with auto-refresh
  - `ads.py` — Google Ads GAQL client
  - `gbp.py` — Google Business Profile client (3 base URLs)
  - `merchant.py` — Merchant Center client
  - `ga4.py` — GA4 Data API client
  - `http.py` — HTTP helpers with auth headers
  - `db.py` — SQLite connection manager
  - `output.py` — table/JSON formatters
  - `timeutil.py` — timezone-aware time helpers
- `fetch_daily.py` — cron-friendly daily data fetcher
- `generate_token.py` — OAuth token generator (4 scopes)

## Key Patterns

- Every command supports `--json` for structured output
- All write operations go through the changelog (`gads log`)
- Snapshots should be taken before mutations (`gads snapshot`)
- Agent enforcement via `GADS_ENFORCE_CALLER=1` restricts CLI to a named agent
- Google Ads API uses REST directly (no protobuf, no client library)
- GBP uses 3 different base URLs (account management, business info, legacy v4)
