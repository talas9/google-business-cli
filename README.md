# google-business-cli

Unified CLI for managing Google Ads, Google Business Profile, Google Merchant Center, and Google Analytics (GA4). Built for AI coding agents (Claude Code, Cursor, etc.) and human operators.

## Features

- **Google Ads**: GAQL queries, performance reports, campaign snapshots, changelog, daily data fetch
- **Google Business Profile**: Accounts, locations, reviews, review replies
- **Google Merchant Center**: Products, feeds, shipping, returns, account status
- **Google Analytics (GA4)**: Reports, realtime data, metadata
- **Agent-ready**: Caller enforcement, JSON output on all commands, `.env`-based config
- **Local-first**: SQLite database for offline queries, git-syncable

## Setup

### 1. Prerequisites

- Python 3.10+
- A Google Cloud project with APIs enabled:
  - Google Ads API
  - My Business Account Management API
  - Content API for Shopping (Merchant Center)
  - Google Analytics Data API

### 2. Install dependencies

```bash
pip install click requests google-auth google-auth-oauthlib python-dotenv
```

### 3. Configure

```bash
cp .env.example .env
# Edit .env with your values
```

### 4. Generate OAuth token

Download `client_secret.json` from [Google Cloud Console](https://console.cloud.google.com/apis/credentials) and save it to `credentials/client_secret.json`.

```bash
python generate_token.py
```

This generates `credentials/google-ads-oauth.json` with scopes for all four Google services.

### 5. Verify

```bash
./gads doctor
```

## Usage

Every command supports `--json` for structured output and `--help` for options.

### Google Ads

```bash
# Run any GAQL query
./gads query "SELECT campaign.name, metrics.clicks FROM campaign WHERE segments.date = '2026-03-25'"

# Performance from local database
./gads perf --days 7
./gads perf --campaign "PMax" --json

# Pull fresh data from API
./gads refresh --days 3
./gads refresh --days 7 --config --push

# Snapshot before making changes
./gads snapshot pre-budget-change --save-file

# Log a change
./gads log "budget_change" "PMax budget 25→30" --reason "Strong CPA"
```

### Google Business Profile

```bash
./gads gbp accounts
./gads gbp locations --account accounts/123456789
./gads gbp location locations/987654321
./gads gbp reviews locations/987654321
./gads gbp reply-review accounts/123/locations/456/reviews/789 "Thank you!"
```

### Merchant Center

```bash
./gads merchant account
./gads merchant status
./gads merchant products --limit 50
./gads merchant product-status
./gads merchant feeds
./gads merchant shipping
./gads merchant returns
```

### GA4

```bash
./gads ga4 metadata
./gads ga4 report --dimensions date --metrics activeUsers,sessions --start 7daysAgo
./gads ga4 realtime --dimensions country --metrics activeUsers
```

## Configuration Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_ADS_DEVELOPER_TOKEN` | Yes | From Google Ads API Center |
| `GOOGLE_ADS_CUSTOMER_ID` | Yes | 10 digits, no dashes |
| `GOOGLE_ADS_LOGIN_CUSTOMER_ID` | For MCC | Manager account ID |
| `GOOGLE_ADS_API_VERSION` | No | Default: `v18` |
| `GOOGLE_MERCHANT_CENTER_ID` | For MC | Merchant Center account ID |
| `GOOGLE_GA4_PROPERTY_ID` | For GA4 | GA4 property ID (digits only) |
| `GADS_TIMEZONE` | No | IANA timezone, default: `UTC` |
| `GADS_PROJECT_ROOT` | No | Parent project root (auto-detected) |
| `GADS_DB_PATH` | No | SQLite path (default: `../data/gads.db`) |
| `GADS_CREDENTIALS_PATH` | No | OAuth token path |
| `GADS_SNAPSHOTS_DIR` | No | Snapshot output directory |

### Agent Enforcement

For multi-agent setups where you want to restrict CLI access:

```bash
GADS_ENFORCE_CALLER=1
GADS_EXPECTED_CALLER=google-platform-operator
GADS_CALLER_AGENT=google-platform-operator  # Set by the calling agent
```

## Architecture

```
google-business-cli/
├── gads                  # Main CLI entry point (Click)
├── gads.sh               # Shell wrapper with .env loading
├── gads_lib/
│   ├── __init__.py       # Public API
│   ├── config.py         # Environment-driven configuration
│   ├── auth.py           # OAuth credential management
│   ├── http.py           # HTTP helpers with auth headers
│   ├── ads.py            # Google Ads GAQL client
│   ├── gbp.py            # Google Business Profile client
│   ├── merchant.py       # Merchant Center client
│   ├── ga4.py            # GA4 Data API client
│   ├── db.py             # SQLite connection
│   ├── output.py         # Table/JSON formatters
│   └── timeutil.py       # Timezone-aware time helpers
├── fetch_daily.py        # Cron-friendly daily data fetch
├── generate_token.py     # OAuth token generator
├── .env.example          # Configuration template
├── CLAUDE.md             # Claude Code project context
└── README.md             # This file
```

## License

MIT
