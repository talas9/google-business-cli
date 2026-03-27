# gads-cli

**Google Ads CLI** — a unified command-line tool for managing Google Ads campaigns, with built-in support for Google Business Profile, Google Merchant Center, and Google Analytics (GA4).

Built for AI coding agents (Claude Code, Cursor, etc.) and human operators. Every command supports `--json` for machine-readable output and `--help` for full documentation.

> The name `gads` stands for **G**oogle **Ads**. While Google Ads is the primary focus, the CLI also provides commands for related Google services (GBP, Merchant Center, GA4) that are commonly used alongside ad campaigns.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-green.svg)](https://python.org)

## Features

| Service | Commands | Description |
|---------|----------|-------------|
| **Google Ads** | `query`, `perf`, `config`, `refresh`, `snapshot`, `log` | GAQL queries, performance reports, campaign snapshots, changelog |
| **Google Business Profile** | `gbp accounts`, `gbp locations`, `gbp reviews`, `gbp reply-review`, `gbp delete-reply` | Manage locations, reviews, and replies |
| **Google Merchant Center** | `merchant account`, `merchant status`, `merchant products`, `merchant feeds`, `merchant shipping`, `merchant returns` | Product listings, feed management, diagnostics |
| **Google Analytics (GA4)** | `ga4 report`, `ga4 realtime`, `ga4 metadata` | Traffic reports, real-time data, available dimensions/metrics |

**Cross-cutting features:**
- `--json` flag on every command for machine-readable output
- `--help` on every command with full option documentation
- `doctor` command to validate credentials and API access
- SQLite database for offline queries and git-syncable data
- Environment-based configuration — zero hardcoded values
- Agent enforcement for multi-agent setups (optional)
- Configurable timezone (IANA format)

## Install

One command — downloads the CLI, detects your AI platforms (Claude Code, gsd-pi, ruflo), installs agents + skills + hooks, and runs auth setup:

```bash
curl -fsSL https://raw.githubusercontent.com/talas9/gads-cli/main/scripts/install.sh | bash
```

The installer is interactive. It will:
1. Download the CLI to `~/.gads-cli/`
2. Install Python dependencies
3. Detect Claude Code, gsd-pi, and ruflo
4. Ask which platforms to wire up (global or project scope)
5. Install a specialized `google-platform-operator` agent + `gads-cli` skill + update hook
6. Run the OAuth setup wizard

### Manual Setup

If you prefer manual installation:

```bash
git clone https://github.com/talas9/gads-cli.git
cd gads-cli
pip install .
cp .env.example .env && $EDITOR .env
python generate_token.py
./gads doctor
```

## Setup

### 1. Prerequisites

- Python 3.10+
- A Google Cloud project with APIs enabled (see below)
- OAuth 2.0 client credentials (`client_secret.json`)
- A Google Ads developer token (from a [Manager Account / MCC](https://ads.google.com/intl/en/home/tools/manager-accounts/))

### Google Cloud Project Setup

1. **Create a project** (if you don't have one): [console.cloud.google.com/projectcreate](https://console.cloud.google.com/projectcreate)

2. **Enable APIs** — click each link and click "ENABLE":

   | API | Required for | Link |
   |-----|-------------|------|
   | Google Ads API | **Required** — all ads commands | [Enable](https://console.cloud.google.com/apis/library/googleads.googleapis.com) |
   | My Business Account Mgmt API | GBP commands | [Enable](https://console.cloud.google.com/apis/library/mybusinessaccountmanagement.googleapis.com) |
   | My Business Business Info API | GBP location details | [Enable](https://console.cloud.google.com/apis/library/mybusinessbusinessinformation.googleapis.com) |
   | My Business v4 (legacy) | GBP reviews, posts, media | [Enable](https://console.cloud.google.com/apis/library/mybusiness.googleapis.com) |
   | Content API for Shopping | Merchant Center commands | [Enable](https://console.cloud.google.com/apis/library/content.googleapis.com) |
   | GA4 Data API | GA4 reports and realtime | [Enable](https://console.cloud.google.com/apis/library/analyticsdata.googleapis.com) |
   | GA4 Admin API | GA4 property metadata | [Enable](https://console.cloud.google.com/apis/library/analyticsadmin.googleapis.com) |

   > You only need to enable the APIs for services you'll use. Google Ads API is required; the rest are optional.

3. **Configure OAuth consent screen**:
   - Go to [APIs & Services → OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent)
   - User Type: **External** (unless you have Google Workspace → Internal)
   - App name: anything (e.g. `gads-cli`)
   - User support email & developer contact: your email
   - Click "SAVE AND CONTINUE" through Scopes
   - On **Test Users**: add your Google account email
   - Click "SAVE AND CONTINUE" → "BACK TO DASHBOARD"
   - Your app stays in "Testing" mode — this is fine, you do NOT need to publish or verify it

4. **Create OAuth credentials**:
   - Go to [APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials)
   - Click **+ CREATE CREDENTIALS** → **OAuth client ID**
   - Application type: **Desktop app**
   - Name: anything (e.g. `gads-cli`)
   - Click **CREATE**, then **DOWNLOAD JSON**
   - Save the file as `credentials/client_secret.json` in your project

### Developer Token Access Levels

Your Google Ads developer token determines which API features you can use:

| Level | Approval | What you get |
|-------|----------|-------------|
| **Test Account** | Instant | Works only with test accounts — not real ad accounts |
| **Basic Access** | Apply, 1-3 days | Campaign management, reporting, audience management, most CLI commands |
| **Standard Access** | Apply, 1-4 weeks | Everything in Basic + Keyword Planner, Keyword Forecasting, Reach Planner, Bidding Strategies API |

**Most commands in this CLI work with Basic Access.** Standard Access is only needed for:
- `gads keyword ideas` — Keyword Planner (generateKeywordIdeas)
- `gads keyword forecast` — Keyword volume forecasting (generateKeywordForecastMetrics)
- Any future commands that use restricted API endpoints

**How to get your token:**
1. **Create a Manager (MCC) account** if you don't have one — developer tokens are created from manager accounts, NOT from regular Google Ads accounts:
   - Go to [ads.google.com/intl/en/home/tools/manager-accounts](https://ads.google.com/intl/en/home/tools/manager-accounts/)
   - Create a manager account (free, takes 2 minutes)
   - Link your Google Ads account(s) to the manager account
2. Log into your **manager account** and go to [Google Ads API Center](https://ads.google.com/aw/apicenter)
3. If you see "Apply for Basic Access" → apply and wait for approval email (1-3 business days)
4. Once approved, copy your developer token
5. If you need Keyword Planner commands, apply for Standard Access after Basic is approved — Google reviews your API usage and may take 1-4 weeks

> **Important:** The developer token lives in your *manager account* (MCC). The `GOOGLE_ADS_LOGIN_CUSTOMER_ID` in your `.env` should be set to the manager account's customer ID. The `GOOGLE_ADS_CUSTOMER_ID` is the actual ad account you want to manage.

### 2. Install

**Option A: pip install (recommended)**
```bash
pip install .
```

**Option B: Direct dependencies**
```bash
pip install click requests google-auth google-auth-oauthlib python-dotenv
```

### 3. Configure

```bash
cp .env.example .env
```

Edit `.env` with your values. At minimum you need:
```bash
GOOGLE_ADS_DEVELOPER_TOKEN=your-developer-token
GOOGLE_ADS_CUSTOMER_ID=1234567890    # 10 digits, no dashes
```

### 4. Generate OAuth token

Place your `client_secret.json` in the `credentials/` directory, then:

```bash
python generate_token.py
```

This opens a browser for Google sign-in and generates `credentials/google-ads-oauth.json` with scopes for all four services (Ads, GBP, Merchant Center, GA4).

### 5. Verify

```bash
./gads doctor
```

## Command Reference

### Core Commands

| Command | Description |
|---------|-------------|
| `gads doctor` | Check credentials, API access, and configuration |
| `gads auth status` | Show credential status (never prints secrets) |
| `gads --version` | Show CLI version |

### Google Ads

```bash
# Run any GAQL query
gads query "SELECT campaign.name, metrics.clicks FROM campaign"

# Performance from local database
gads perf --days 7
gads perf --campaign "my-campaign" --json

# Pull fresh data from API into local DB
gads refresh --days 3
gads refresh --days 7 --config --push

# Snapshot campaign configs before making changes
gads snapshot pre-budget-change --save-file

# Log a change to the changelog
gads log "budget_change" "PMax budget 25→30" --reason "Strong CPA"

# Show current campaign configs from API
gads config --json
```

### Google Business Profile

```bash
# List all GBP accounts
gads gbp accounts

# List locations for an account
gads gbp locations --account accounts/123456789

# Get a specific location's details
gads gbp location locations/987654321

# List reviews for a location
gads gbp reviews locations/987654321

# Reply to a review
gads gbp reply-review accounts/123/locations/456/reviews/789 "Thank you!"

# Delete a review reply
gads gbp delete-reply accounts/123/locations/456/reviews/789
```

### Google Merchant Center

```bash
# Account info
gads merchant account

# Account diagnostics and issues
gads merchant status

# List products
gads merchant products --limit 50

# Product approval statuses
gads merchant product-status

# Data feeds
gads merchant feeds

# Shipping settings
gads merchant shipping

# Return policies
gads merchant returns
```

### Google Analytics (GA4)

```bash
# Available dimensions and metrics
gads ga4 metadata

# Run a report
gads ga4 report --dimensions date --metrics activeUsers,sessions --start 7daysAgo --end yesterday

# Real-time data
gads ga4 realtime --dimensions country --metrics activeUsers
```

### Automation

```bash
# Daily data fetch (use with cron)
python fetch_daily.py --days 3
python fetch_daily.py --days 7 --config --push

# Cron example (fetch at 3:30 AM daily):
# 30 3 * * * cd /path/to/project && python gads-cli/fetch_daily.py --days 3 --push
```

## Configuration Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_ADS_DEVELOPER_TOKEN` | Yes | — | From [Google Ads API Center](https://ads.google.com/aw/apicenter) |
| `GOOGLE_ADS_CUSTOMER_ID` | Yes | — | 10-digit account ID (no dashes) |
| `GOOGLE_ADS_LOGIN_CUSTOMER_ID` | For MCC | — | Manager (MCC) account ID |
| `GOOGLE_ADS_API_VERSION` | No | `v19` | Google Ads API version |
| `GOOGLE_MERCHANT_CENTER_ID` | For MC | — | Merchant Center account ID |
| `GOOGLE_GA4_PROPERTY_ID` | For GA4 | — | GA4 property ID (digits only) |
| `GADS_TIMEZONE` | No | `UTC` | IANA timezone (e.g. `America/New_York`, `Asia/Dubai`) |
| `GADS_CURRENCY` | No | `USD` | ISO 4217 currency code (e.g. `USD`, `AED`, `EUR`, `GBP`) |
| `GADS_PROJECT_ROOT` | No | auto | Parent project root directory |
| `GADS_DB_PATH` | No | `../data/gads.db` | SQLite database path |
| `GADS_CREDENTIALS_PATH` | No | `../credentials/google-ads-oauth.json` | OAuth token path |
| `GADS_SNAPSHOTS_DIR` | No | `../snapshots` | Snapshot output directory |

### Agent Enforcement (Optional)

For multi-agent setups where you want to restrict CLI access to a specific agent:

```bash
GADS_ENFORCE_CALLER=1
GADS_EXPECTED_CALLER=my-operator-agent
GADS_CALLER_AGENT=my-operator-agent  # Set by the calling agent
```

When `GADS_ENFORCE_CALLER=1`, the CLI verifies `GADS_CALLER_AGENT` matches `GADS_EXPECTED_CALLER` before executing any command.

## Architecture

```
gads-cli/
├── gads                  # Main CLI entry point (Click)
├── gads.sh               # Shell wrapper with .env loading
├── gads_lib/
│   ├── __init__.py       # Public API — re-exports all modules
│   ├── cli.py            # Entry point for pip-installed command
│   ├── config.py         # Environment-driven configuration
│   ├── auth.py           # OAuth credential management
│   ├── http.py           # HTTP helpers with auth headers
│   ├── ads.py            # Google Ads GAQL client
│   ├── gbp.py            # Google Business Profile client
│   ├── merchant.py       # Merchant Center client
│   ├── ga4.py            # GA4 Data API client
│   ├── db.py             # SQLite connection manager
│   ├── output.py         # Table/JSON formatters
│   └── timeutil.py       # Timezone-aware time helpers
├── fetch_daily.py        # Cron-friendly daily data fetcher
├── generate_token.py     # OAuth token generator (4 scopes)
├── pyproject.toml        # Python package configuration
├── .env.example          # Configuration template
├── CLAUDE.md             # Claude Code project context
├── CHANGELOG.md          # Version history
└── README.md             # This file
```

## Using with Claude Code

This CLI is designed to work seamlessly with [Claude Code](https://claude.ai/code). The included `CLAUDE.md` provides Claude with full context about the CLI's commands, architecture, and configuration.

```bash
# Claude can use the CLI directly:
claude "Run gads perf --days 7 and analyze the trends"
claude "Check my GBP reviews and draft replies for any negative ones"
claude "Pull fresh data and compare this week vs last week"
```

For automated agent workflows, use the agent enforcement feature to restrict CLI access to a designated operator agent.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Run the doctor check (`./gads doctor`)
5. Commit and push
6. Open a Pull Request

## License

MIT — see [LICENSE](LICENSE) for details.
