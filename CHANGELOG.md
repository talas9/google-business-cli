# Changelog

All notable changes to this project will be documented in this file.

## [2.1.0] - 2026-03-27

### Added
- **`GADS_CURRENCY`** env var for configurable currency (ISO 4217, default: USD)
- **Dynamic versioning**: `__version__` in `gads_lib/__init__.py` is the single source of truth
- Currency shown in `doctor` and `auth status` output

### Changed
- CLI logic moved into `gads_lib/cli.py` — proper Python module, pip install works correctly
- `gads` root script is now a thin shim importing from `gads_lib.cli`
- `pyproject.toml` reads version dynamically from `gads_lib.__version__`
- DB columns: `cost_aed` → `cost`, `budget_aed` → `budget` (generic, currency-agnostic)

### Fixed
- `pip install` now works — was broken by invalid build backend and missing CLI module

## [2.0.0] - 2026-03-26

### Added
- **Google Business Profile commands**: `gbp accounts`, `gbp locations`, `gbp location`, `gbp reviews`, `gbp reply-review`, `gbp delete-reply`
- **Google Merchant Center commands**: `merchant account`, `merchant status`, `merchant products`, `merchant product-status`, `merchant feeds`, `merchant shipping`, `merchant returns`
- **Google Analytics 4 commands**: `ga4 metadata`, `ga4 report`, `ga4 realtime`
- **Modular library** (`gads_lib/`): Separate modules for auth, ads, gbp, merchant, ga4, http, db, output, config, timeutil
- **`doctor` command**: Validates credentials, API access, and configuration
- **`auth status` command**: Shows credential status (never prints secrets)
- **Agent enforcement**: Optional caller restriction via `GADS_ENFORCE_CALLER`
- **`fetch_daily.py`**: Standalone cron-friendly daily data fetcher
- **`generate_token.py`**: OAuth token generator with all 4 scopes
- **Full environment configuration**: All settings via `.env` — no hardcoded values
- **`pyproject.toml`**: pip-installable package
- **`--json` flag** on all commands for machine-readable output
- **Shell wrapper** (`gads.sh`): Auto-loads `.env` before running CLI

### Changed
- All hardcoded account IDs, timezone, and paths replaced with environment variables
- API version default updated to v19
- Timezone handling uses IANA names (configurable via `GADS_TIMEZONE`)
- Database path configurable via `GADS_DB_PATH`

## [1.0.0] - 2026-02-11

### Added
- Initial CLI with 6 commands: `query`, `log`, `snapshot`, `perf`, `config`, `refresh`
- Google Ads GAQL query execution
- SQLite-backed performance data and changelog
- OAuth credential management
