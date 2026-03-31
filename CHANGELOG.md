# Changelog

All notable changes to this project will be documented in this file.

## [3.3.0] - 2026-03-31

### Added
- **GBP Performance API** (4 new commands):
  - `gbp perf` — daily performance metrics for a single location
  - `gbp perf-all` — daily metrics for ALL locations with auto-discovery
  - `gbp search-keywords` — monthly search keyword impressions
  - `gbp metrics-list` — list all available daily metrics
- **Google Search Console** (4 new commands, new `gsc` command group):
  - `gsc sites` — list verified Search Console sites
  - `gsc queries` — top search queries with clicks, impressions, CTR, position
  - `gsc pages` — top pages performance
  - `gsc performance` — daily performance time series
- New OAuth scope: `webmasters.readonly` (Search Console access)
- New GCP API: Business Profile Performance API added to `auth setup`
- New GCP API: Search Console API added to `auth setup`
- `auth test` now tests Search Console access
- Scope display in `auth login` now shows Search Console grant status

### Changed
- Total commands: 65 → 73 across 15 groups (was 14)
- OAuth SCOPES list: 4 → 5 scopes

## [3.2.0] - 2026-03-28

### Changed
- README: accurate access level documentation (Test/Explorer/Basic/Standard)
- README: Features table now shows all 65 commands across 14 groups
- README: Command Requirements table shows auth needs per command
- CLAUDE.md: AI-agent-friendly reference with full command taxonomy
- CLAUDE.md: GAQL patterns, known gotchas, architecture overview

### Added
- CI pipeline (`.github/workflows/ci.yml`): Python 3.10-3.13 × Ubuntu + macOS
- CI: syntax check, import verification, secret scanning, version validation
- April 2026 Customer Match deprecation warning in docs

## [3.1.0] - 2026-03-27

### Added
- `audience create` — create CRM-based Customer Match user lists
- `audience upload` — full CSV upload pipeline (phone normalization, name validation, SHA-256 hashing, consent, batch retry with 429 backoff)
- `audience job-status` — check Customer Match upload job status and match rate
- `ads.py`: `audience_find_list()`, `audience_create_list()`, `audience_upload_csv()`
- Phone normalization for UAE formats (05X, 5X, 971X, 00971X, +971X)
- Name validation (`is_valid_name`) — rejects companies, garbage, special chars

## [3.0.0] - 2026-03-27

### Added
- **50+ new commands** across 10 new groups
- `campaign list`, `status`, `budget`, `perf` — campaign management
- `adgroup list`, `status`, `create` — ad group management
- `ad list`, `status`, `perf` — ad management with creatives
- `keyword list`, `add`, `remove`, `negative`, `search-terms`, `ideas`, `forecast` — keyword management and research
- `asset list`, `sitelink`, `callout`, `call` — asset management with two-step extension creation
- `conversion list`, `create`, `tag`, `perf`, `upload` — conversion tracking and offline upload
- `audience list` — user list / audience listing
- `report geo`, `hourly`, `devices`, `search-terms` — specialized reports
- `mutate`, `batch-mutate` — generic escape hatches for any API mutation
- `accounts` — list accessible Google Ads accounts
- `ads.py`: `ads_mutate()`, `ads_batch_mutate()`, `ads_search()`, `ads_upload_click_conversions()`, `generate_keyword_ideas()`, `generate_keyword_forecast()`, `sanitize_keyword()`
- Mutation safety: `--dry-run`, `--yes`, auto-changelog logging, caller enforcement

### Changed
- Repo renamed: `google-business-cli` → `gads-cli`
- All internal references updated to `gads-cli`

## [2.2.0] - 2026-03-27

### Added
- Scope-aware configuration: auto-detects project vs global (`~/.config/gads/`)
- `auth setup` wizard detects scope and writes `.env` to correct location
- Currency step in setup wizard
- Developer token access level guide in setup wizard (Test/Basic/Standard + MCC requirement)

### Fixed
- Global pip install now uses `~/.config/gads/` for credentials/data/snapshots
- `auth setup` no longer writes to site-packages directory

## [2.1.0] - 2026-03-27

### Added
- `GADS_CURRENCY` env var (ISO 4217, default: USD)
- Dynamic versioning from `gads_lib.__version__`

### Changed
- CLI logic moved into `gads_lib/cli.py` — proper pip install
- DB columns: `cost_aed` → `cost`, `budget_aed` → `budget`

### Fixed
- `pip install` broken by invalid build backend and missing CLI module

## [2.0.0] - 2026-03-26

### Added
- Google Business Profile: `gbp accounts`, `locations`, `location`, `reviews`, `reply-review`, `delete-reply`
- Google Merchant Center: `merchant account`, `status`, `products`, `product-status`, `feeds`, `shipping`, `returns`
- Google Analytics 4: `ga4 metadata`, `report`, `realtime`
- Modular library (`gads_lib/`), `doctor`, `auth status`, agent enforcement
- `fetch_daily.py`, `generate_token.py`, `pyproject.toml`, `--json` on all commands

### Changed
- All config via environment variables — zero hardcoded values

## [1.0.0] - 2026-02-11

### Added
- Initial CLI: `query`, `log`, `snapshot`, `perf`, `config`, `refresh`
- Google Ads GAQL queries, SQLite database, OAuth credentials
