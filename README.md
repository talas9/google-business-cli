# gads-cli

**Google Ads CLI** — a unified command-line tool for managing Google Ads campaigns, with built-in support for Google Business Profile, Google Merchant Center, and Google Analytics (GA4).

Built for AI coding agents (Claude Code, Cursor, etc.) and human operators. Every command supports `--json` for machine-readable output and `--help` for full documentation.

> The name `gads` stands for **G**oogle **Ads**. While Google Ads is the primary focus, the CLI also provides commands for related Google services (GBP, Merchant Center, GA4) that are commonly used alongside ad campaigns.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-green.svg)](https://python.org)
[![CI](https://github.com/talas9/gads-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/talas9/gads-cli/actions/workflows/ci.yml)

---

## Features

**65 commands** across 14 groups covering the full Google Ads operational surface:

| Group | Commands | Description |
|-------|----------|-------------|
| **Core** | `query`, `perf`, `config`, `refresh`, `snapshot`, `log`, `accounts`, `doctor` | GAQL queries, local DB reports, campaign snapshots, changelog, account listing |
| **Campaign** | `campaign list`, `status`, `budget`, `perf` | List, enable/pause, change budget, campaign-level metrics from API |
| **Ad Group** | `adgroup list`, `status`, `create` | List, enable/pause, create ad groups |
| **Ad** | `ad list`, `status`, `perf` | List ads with creatives, enable/pause, ad-level metrics |
| **Keyword** | `keyword list`, `add`, `remove`, `negative`, `search-terms`, `ideas`★, `forecast`★ | Keyword management, search terms report, Keyword Planner research |
| **Asset** | `asset list`, `sitelink`, `callout`, `call` | List assets, add sitelinks/callouts/call extensions (two-step creation) |
| **Conversion** | `conversion list`, `create`, `tag`, `perf`, `upload` | Conversion actions, tracking tags, performance by action, offline upload |
| **Audience** | `audience list`, `create`, `upload`, `job-status` | Customer Match user lists, CSV upload with SHA-256 hashing + consent |
| **Report** | `report geo`, `hourly`, `devices`, `search-terms` | Geographic, hourly, device, and search term performance breakdowns |
| **Mutate** | `mutate <type> <json>`, `batch-mutate <json>` | Generic escape hatch for any Google Ads API mutation |
| **GBP** | `gbp accounts`, `locations`, `location`, `reviews`, `reply-review`, `delete-reply` | Google Business Profile management — no dev token needed |
| **Merchant** | `merchant account`, `status`, `products`, `product-status`, `feeds`, `shipping`, `returns` | Merchant Center diagnostics — no dev token needed |
| **GA4** | `ga4 report`, `realtime`, `metadata` | Google Analytics 4 reporting — no dev token needed |
| **Auth** | `auth status`, `setup`, `login`, `revoke`, `test` | Interactive setup wizard, OAuth flow, credential diagnostics |

> ★ Requires Standard Access developer token

**Cross-cutting:**
- `--json` on every command for machine-readable output
- `--dry-run` and `--yes` on all mutation commands
- Auto-logging to changelog after successful mutations
- Scope-aware config — auto-detects project (`./`) vs global (`~/.config/gads/`)
- Agent caller enforcement for multi-agent architectures (optional)
- Configurable timezone (IANA) and currency (ISO 4217)

---

## Install

### One-liner (recommended)

```bash
pip install git+https://github.com/talas9/gads-cli.git
```

### Interactive installer

Downloads the CLI, detects your AI platforms (Claude Code, gsd-pi), wires up agents + skills, and runs auth setup:

```bash
curl -fsSL https://raw.githubusercontent.com/talas9/gads-cli/main/scripts/install.sh | bash
```

### From source

```bash
git clone https://github.com/talas9/gads-cli.git
cd gads-cli
pip install .
```

### Upgrade

```bash
pip install --upgrade git+https://github.com/talas9/gads-cli.git
```

### Pin a version

```bash
pip install git+https://github.com/talas9/gads-cli.git@v3.2.0
```

---

## Quick Start

```bash
# 1. Run the interactive setup wizard (walks through everything)
gads auth setup

# 2. Verify
gads doctor

# 3. Try it
gads campaign list
gads perf --days 7
gads query "SELECT campaign.name, metrics.clicks FROM campaign"
```

The setup wizard handles: GCP project creation, API enablement, OAuth consent screen, credential download, developer token, customer IDs, timezone, currency, and OAuth login — all interactively.

If you prefer manual setup, see [Manual Setup](#manual-setup) below.

---

## Command Reference

### Core

```bash
gads doctor                          # Check credentials, config, API access
gads auth status --json              # Credential status (never prints secrets)
gads accounts                        # List accessible Google Ads accounts
gads query "SELECT campaign.name FROM campaign"  # Run any GAQL query
gads perf --days 7                   # Performance from local database
gads config --json                   # Campaign configs from API
gads refresh --days 3                # Pull API data into local DB
gads snapshot pre-change --save-file # Snapshot configs before mutations
gads log "action" "details"          # Append to changelog
```

### Campaign Management

```bash
gads campaign list                   # All campaigns with status/budget
gads campaign perf --days 7          # Campaign metrics from API
gads campaign status 12345 PAUSED    # Pause a campaign (--dry-run, --yes)
gads campaign budget 12345 25.00     # Change daily budget (--dry-run, --yes)
```

### Ad Groups & Ads

```bash
gads adgroup list --campaign 12345   # List ad groups in a campaign
gads adgroup create 12345 "My Group" # Create ad group
gads adgroup status 67890 PAUSED     # Pause an ad group
gads ad list --campaign 12345        # List ads with creatives
gads ad perf --days 7                # Ad-level performance
gads ad status 67890 11111 PAUSED    # Pause an ad
```

### Keywords

```bash
gads keyword list --campaign 12345 --days 30  # Keyword performance
gads keyword add 67890 "tesla parts" -m PHRASE  # Add keyword to ad group
gads keyword remove 67890 99999               # Remove by criterion ID
gads keyword negative 12345 "free" -m BROAD   # Add negative keyword
gads keyword search-terms --days 7 --min-clicks 2  # Search terms report
gads keyword ideas -k "tesla parts,used parts" --geo 2784  # Keyword Planner ★
gads keyword forecast -k "tesla parts" --geo 2784           # Volume forecast ★
```

### Assets & Extensions

```bash
gads asset list                      # List all assets
gads asset list --type SITELINK      # Filter by type
gads asset sitelink 12345 --link-text "Contact Us" --url "https://..." --desc1 "..."
gads asset callout 12345 --text "Free Shipping"
gads asset call 12345 --phone "+1234567890" --country-code US
```

### Conversions

```bash
gads conversion list                 # All conversion actions
gads conversion perf --days 7        # Performance by conversion action
gads conversion tag 12345            # Get tracking snippet
gads conversion create "My Action" --type WEBPAGE
gads conversion upload --gclid xxx --action-id yyy --time "2026-03-27T12:00:00"
```

### Audiences (Customer Match)

```bash
gads audience list                   # All user lists with sizes/match rates
gads audience create "My List" --life-span 540
gads audience upload data.csv --list-name "My List" --create  # Full pipeline
gads audience job-status 12345       # Check upload job status
```

CSV format: `Phone,Email,First Name,Last Name,Country` — all PII is SHA-256 hashed automatically.

### Reports

```bash
gads report geo --days 7             # Geographic breakdown
gads report hourly --days 7          # Hourly performance
gads report devices --days 7         # Device breakdown
gads report search-terms --days 7    # Search terms report
```

### Generic Mutations (escape hatch)

```bash
gads mutate campaigns '[{"update": {"resourceName": "...", "status": "PAUSED"}, "updateMask": "status"}]'
gads batch-mutate '[{"campaignOperation": {"update": ...}}]'
```

### Google Business Profile

```bash
gads gbp accounts
gads gbp locations --account accounts/123456789
gads gbp location locations/987654321
gads gbp reviews locations/987654321
gads gbp reply-review accounts/123/locations/456/reviews/789 "Thank you!"
gads gbp delete-reply accounts/123/locations/456/reviews/789
```

### Google Merchant Center

```bash
gads merchant account                # Account info
gads merchant status                 # Account issues
gads merchant products --limit 50    # Product listings
gads merchant product-status         # Approval statuses
gads merchant feeds                  # Data feeds
gads merchant shipping               # Shipping settings
gads merchant returns                # Return policy
```

### Google Analytics (GA4)

```bash
gads ga4 metadata                    # Available dimensions/metrics
gads ga4 report -d date -m activeUsers,sessions --start 7daysAgo
gads ga4 realtime -d country -m activeUsers
```

### Automation (cron)

```bash
# Daily data fetch
python fetch_daily.py --days 3 --push

# Cron example (3:30 AM daily)
30 3 * * * cd /path/to/project && gads refresh --days 3 --push
```

---

## Configuration

All configuration via environment variables or `.env` file. See [`.env.example`](.env.example).

### Required vs Optional

| Variable | Required for | Description |
|----------|-------------|-------------|
| `GOOGLE_ADS_DEVELOPER_TOKEN` | **All Google Ads commands** | Developer token from [API Center](https://ads.google.com/aw/apicenter) |
| `GOOGLE_ADS_CUSTOMER_ID` | **All Google Ads commands** | 10-digit account ID (no dashes) |
| `GOOGLE_ADS_LOGIN_CUSTOMER_ID` | MCC setups | Manager account ID |
| `GOOGLE_MERCHANT_CENTER_ID` | Merchant Center commands | MC account ID |
| `GOOGLE_GA4_PROPERTY_ID` | GA4 commands | Property ID (digits only) |
| `GADS_TIMEZONE` | Optional (default: `UTC`) | IANA timezone (e.g. `America/New_York`) |
| `GADS_CURRENCY` | Optional (default: `USD`) | ISO 4217 code (e.g. `AED`, `EUR`) |
| `GOOGLE_ADS_API_VERSION` | Optional (default: `v19`) | API version |

> **GBP, Merchant Center, and GA4 commands do NOT need a developer token** — only OAuth credentials.

### Which commands need what

| Commands | Dev token | OAuth scope | Min access level |
|----------|-----------|-------------|-----------------|
| `gbp *` | No | `business.manage` | — |
| `merchant *` | No | `content` | — |
| `ga4 *` | No | `analytics.readonly` | — |
| `query`, `perf`, `campaign *`, `adgroup *`, `ad *`, `report *` | Yes | `adwords` | Explorer |
| `keyword add/remove/negative/search-terms` | Yes | `adwords` | Explorer |
| `keyword ideas`, `keyword forecast` | Yes | `adwords` | **Standard** |
| `audience upload` | Yes | `adwords` | Basic |
| `campaign status/budget`, `asset *`, `mutate *` | Yes | `adwords` | Explorer |

### Agent Enforcement (optional)

```bash
GADS_ENFORCE_CALLER=1
GADS_EXPECTED_CALLER=my-operator-agent
GADS_CALLER_AGENT=my-operator-agent  # Set by the calling agent
```

---

## Manual Setup

If you prefer not to use `gads auth setup`, here's the manual process:

### 1. Prerequisites

- Python 3.10+
- A [Google Cloud project](https://console.cloud.google.com/projectcreate)
- A [Google Ads Manager (MCC) account](https://ads.google.com/intl/en/home/tools/manager-accounts/) for the developer token

### 2. Enable APIs

Click each link → click "ENABLE" (only enable what you need):

| API | For | Link |
|-----|-----|------|
| Google Ads API | **Required** | [Enable](https://console.cloud.google.com/apis/library/googleads.googleapis.com) |
| My Business Account Mgmt API | GBP | [Enable](https://console.cloud.google.com/apis/library/mybusinessaccountmanagement.googleapis.com) |
| My Business Business Info API | GBP | [Enable](https://console.cloud.google.com/apis/library/mybusinessbusinessinformation.googleapis.com) |
| My Business v4 (legacy) | GBP reviews | [Enable](https://console.cloud.google.com/apis/library/mybusiness.googleapis.com) |
| Content API for Shopping | Merchant Center | [Enable](https://console.cloud.google.com/apis/library/content.googleapis.com) |
| GA4 Data API | GA4 | [Enable](https://console.cloud.google.com/apis/library/analyticsdata.googleapis.com) |
| GA4 Admin API | GA4 | [Enable](https://console.cloud.google.com/apis/library/analyticsadmin.googleapis.com) |

### 3. OAuth Consent Screen

1. Go to [OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent)
2. User Type: **External**
3. App name, support email, developer contact → fill in
4. Scopes → skip
5. Test Users → **add your Google account email**
6. Save → your app stays in "Testing" mode (fine, no need to publish)

### 4. OAuth Credentials

1. Go to [Credentials](https://console.cloud.google.com/apis/credentials)
2. **+ CREATE CREDENTIALS** → **OAuth client ID** → **Desktop app**
3. **DOWNLOAD JSON** → save as `credentials/client_secret.json`

### 5. Developer Token

Developer tokens are created from **Manager (MCC) accounts**, not regular ad accounts.

1. [Create an MCC](https://ads.google.com/intl/en/home/tools/manager-accounts/) if you don't have one
2. Link your ad account(s) to it
3. Go to [API Center](https://ads.google.com/aw/apicenter) in the MCC
4. Apply for Basic Access (1-3 days approval)
5. Copy the token → set `GOOGLE_ADS_DEVELOPER_TOKEN` in `.env`

#### Access Levels

| Level | Approval | Ops/day | What you get |
|-------|----------|---------|-------------|
| **Test** | Instant | 15,000 | Test accounts only |
| **Explorer** | Auto | 2,880 prod | Most features — sufficient for basic automation |
| **Basic** | ~2 days | 15,000 | Production access, most CLI commands |
| **Standard** | ~10 days | Unlimited | + Keyword Planner, Audience Insights, Reach Planner, Billing |

### 6. Configure & Login

```bash
cp .env.example .env   # Edit with your values
gads auth login        # Opens browser for OAuth
gads doctor            # Verify everything
```

> ⚠️ **Customer Match deprecation:** Starting April 1, 2026, `audience upload` will fail if your token has never sent a successful Customer Match request. Upload before that date or switch to Data Manager API.

---

## Architecture

```
gads-cli/
├── gads                  # CLI entry point (thin shim)
├── gads.sh               # Shell wrapper with .env loading
├── gads_lib/
│   ├── __init__.py       # Version + public API exports
│   ├── cli.py            # All Click command groups (65 commands)
│   ├── config.py         # Scope-aware env config
│   ├── auth.py           # OAuth credential management
│   ├── ads.py            # Google Ads REST client + GAQL + mutations
│   ├── gbp.py            # GBP client (3 base URLs)
│   ├── merchant.py       # Merchant Center client
│   ├── ga4.py            # GA4 Data API client
│   ├── http.py           # HTTP helpers with auth headers
│   ├── db.py             # SQLite connection manager
│   ├── output.py         # Table/JSON formatters
│   └── timeutil.py       # Timezone-aware helpers
├── fetch_daily.py        # Cron-friendly daily data fetcher
├── generate_token.py     # OAuth token generator (4 scopes)
├── scripts/install.sh    # Interactive installer
├── .github/workflows/    # CI pipeline
├── pyproject.toml        # Package metadata
├── .env.example          # Configuration template
├── CLAUDE.md             # AI agent reference
├── CHANGELOG.md          # Version history
└── README.md
```

Uses Google REST APIs directly (`requests` + `google-auth`) — no protobuf, no `google-ads` client library.

---

## Using with Claude Code

The included `CLAUDE.md` gives Claude full context about commands, auth, and known gotchas.

```bash
claude "Run gads perf --days 7 and analyze the trends"
claude "Check my GBP reviews and draft replies for any negative ones"
claude "Pull fresh data and compare this week vs last week"
```

---

## Contributing

1. Fork → feature branch → make changes
2. `gads doctor` to verify
3. Push → open PR

CI runs Python 3.10-3.13 on Ubuntu + macOS automatically.

## License

MIT — see [LICENSE](LICENSE).
