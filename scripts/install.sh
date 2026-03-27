#!/usr/bin/env bash
# gads-cli installer
#
# Install:
#   curl -fsSL https://raw.githubusercontent.com/talas9/gads-cli/main/scripts/install.sh | bash
#
# Interactive — detects Claude Code, gsd-pi, ruflo. Asks where to install,
# wires agents + skills + hooks, runs auth setup.
#
set -euo pipefail

REPO_URL="https://github.com/talas9/gads-cli.git"
DEFAULT_DIR="$HOME/.gads-cli"
VERSION="2.0.0"

# ── Flags ────────────────────────────────────────────────────
PROJECT_SCOPE=false
SKIP_AUTH=false
INSTALL_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project)    PROJECT_SCOPE=true; shift ;;
    --skip-auth)  SKIP_AUTH=true; shift ;;
    --dir)        INSTALL_DIR="$2"; shift 2 ;;
    --help|-h)
      cat <<EOF
gads-cli installer v${VERSION}

Usage:
  curl -fsSL https://raw.githubusercontent.com/talas9/gads-cli/main/scripts/install.sh | bash

Options:
  --project     Install agents into current project instead of global
  --dir PATH    Custom CLI install location
  --skip-auth   Skip OAuth setup (for CI/testing)

Detects Claude Code, gsd-pi, and ruflo automatically.
EOF
      exit 0 ;;
    *) echo "Unknown: $1"; exit 1 ;;
  esac
done

# ── Helpers ──────────────────────────────────────────────────
R="\033[0m"; B="\033[1m"; D="\033[2m"
CC="\033[36m"; CG="\033[32m"; CY="\033[33m"; CR="\033[31m"

ok()   { echo -e "  ${CG}✓${R} $1"; }
warn() { echo -e "  ${CY}⚠${R} $1"; }
err()  { echo -e "  ${CR}✗${R} $1"; }
step() { echo -e "\n  ${B}[$1/$2]${R} $3\n"; }

prompt() {
  local q="$1" default="$2" answer
  if [[ -t 0 ]]; then
    echo -ne "  $q [$default]: " >&2; read -r answer || answer=""
    echo "${answer:-$default}"
  else
    echo "$default"
  fi
}

# ── Banner ───────────────────────────────────────────────────
echo ""
echo -e "  ${CC}╔══════════════════════════════════════════════════════╗${R}"
echo -e "  ${CC}║${R}  ${B}gads-cli${R} v${VERSION}                         ${CC}║${R}"
echo -e "  ${CC}║${R}  Unified CLI: Google Ads · GBP · Merchant · GA4      ${CC}║${R}"
echo -e "  ${CC}╚══════════════════════════════════════════════════════╝${R}"

# ── Step 1: Prerequisites ───────────────────────────────────
step 1 6 "Prerequisites"

PY=""
command -v python3 &>/dev/null && PY="python3"
[[ -z "$PY" ]] && command -v python &>/dev/null && PY="python"
if [[ -z "$PY" ]]; then
  err "Python 3.10+ required. Install: https://python.org/downloads/"; exit 1
fi
ok "Python $($PY --version 2>&1 | cut -d' ' -f2)"

command -v git &>/dev/null || { err "git required"; exit 1; }
ok "git $(git --version | cut -d' ' -f3)"

# ── Step 2: Download ────────────────────────────────────────
step 2 6 "Download CLI"

CLI_DIR="${INSTALL_DIR:-$DEFAULT_DIR}"

if [[ -f "$CLI_DIR/gads" ]]; then
  ok "Found at $CLI_DIR"
  if [[ "$(prompt "Pull latest?" "Y/n")" =~ ^[Yy] ]]; then
    git -C "$CLI_DIR" pull --quiet 2>/dev/null && ok "Updated" || warn "Pull failed — using existing"
  fi
else
  echo "  Cloning to $CLI_DIR..."
  git clone --quiet --depth 1 "$REPO_URL" "$CLI_DIR"
  ok "Downloaded"
fi

chmod +x "$CLI_DIR/gads" "$CLI_DIR/gads.sh" 2>/dev/null || true

# ── Step 3: Dependencies ────────────────────────────────────
step 3 6 "Python dependencies"

$PY -m pip install --quiet --user click requests google-auth google-auth-oauthlib python-dotenv 2>/dev/null \
  && ok "Installed" \
  || warn "pip had issues — run: pip install click requests google-auth google-auth-oauthlib python-dotenv"

# ── Step 4: Detect platforms ────────────────────────────────
step 4 6 "Detect AI platforms"

HAS_CLAUDE=false; HAS_GSD=false; HAS_RUFLO=false
command -v claude &>/dev/null && HAS_CLAUDE=true && ok "Claude Code"
command -v gsd    &>/dev/null && HAS_GSD=true    && ok "gsd-pi"
command -v ruflo  &>/dev/null && HAS_RUFLO=true  && ok "ruflo"
$HAS_CLAUDE || $HAS_GSD || $HAS_RUFLO || warn "No AI platforms found — standalone install"

# ── Step 5: Wire agents + skills + hooks ─────────────────────
step 5 6 "Install agents & skills"

# Scope
SCOPE="global"
if $PROJECT_SCOPE; then
  SCOPE="project"
elif [[ -t 0 ]] && ($HAS_CLAUDE || $HAS_GSD || $HAS_RUFLO); then
  echo "  Scope:"
  echo "    1) Global  — all projects (~/.claude, ~/.gsd)"
  echo "    2) Project — this directory only"
  echo ""
  [[ "$(prompt "Choice" "1")" == "2" ]] && SCOPE="project"
fi
ok "Scope: $SCOPE"
echo ""

# ── Agent template ───────────────────────────────────────────
write_agent() {
  local dir="$1"
  mkdir -p "$dir"
  cat > "$dir/google-platform-operator.md" << 'ENDAGENT'
---
name: google-platform-operator
description: >
  Use for ALL Google Ads, Google Business Profile, Merchant Center, and GA4
  operations. Runs the gads CLI for queries, mutations, reporting, review
  management, and product checks.
model: inherit
tools: Bash, Read
---

You are the Google platform operator. You have exclusive access to the `gads`
CLI for all Google Ads, Business Profile, Merchant Center, and GA4 operations.

## CLI Location

ENDAGENT
  # Append dynamic path (not in heredoc to avoid escaping issues)
  echo "\`$CLI_DIR/gads\`" >> "$dir/google-platform-operator.md"
  cat >> "$dir/google-platform-operator.md" << 'ENDAGENT2'

## Quick Reference

```bash
gads --help              # All commands
gads doctor              # Verify setup
gads auth test           # Test API access

# Google Ads
gads query "SELECT campaign.name, metrics.clicks FROM campaign"
gads perf --days 7 --json
gads refresh --days 3

# GBP
gads gbp accounts --json
gads gbp reviews locations/ID --json
gads gbp reply-review accounts/X/locations/Y/reviews/Z "Reply"

# Merchant Center
gads merchant products --json
gads merchant status --json

# GA4
gads ga4 report -d date -m activeUsers --start 7daysAgo --json
gads ga4 realtime --json
```

## Rules
- Use `--json` when output is processed programmatically
- Snapshot before changes: `gads snapshot pre-change`
- Log all mutations: `gads log "action" "details"`
- Never print credentials — use `gads auth status`
- If a command fails, run `gads doctor` first
ENDAGENT2

  # Replace generic 'gads' with full path in the file
  sed -i "s|^gads |$CLI_DIR/gads |g" "$dir/google-platform-operator.md"

  ok "Agent → $dir/google-platform-operator.md"
}

# ── Skill template ───────────────────────────────────────────
write_skill() {
  local dir="$1/gads-cli"
  mkdir -p "$dir"
  cat > "$dir/SKILL.md" << ENDSKILL
---
name: gads-cli
description: >
  Use when the user asks about Google Ads campaigns, performance, keywords,
  GBP reviews, Merchant Center products, or GA4 analytics. Triggers on:
  "google ads", "campaign performance", "GBP reviews", "merchant center",
  "GA4 report", "ad spend", "search terms", "business profile".
---

# Google Business CLI

Unified CLI at \`$CLI_DIR/gads\` for Google Ads, GBP, Merchant Center, and GA4.

\`\`\`bash
$CLI_DIR/gads --help          # All commands
$CLI_DIR/gads doctor          # Check setup
$CLI_DIR/gads auth setup      # Interactive credential wizard
\`\`\`

| Group | Commands |
|-------|---------|
| Google Ads | query, perf, config, refresh, snapshot, log |
| GBP | gbp accounts/locations/reviews/reply-review/delete-reply |
| Merchant | merchant account/status/products/feeds/shipping/returns |
| GA4 | ga4 report/realtime/metadata |
| Auth | auth setup/login/test/status/revoke |
| Doctor | doctor (readiness check) |

Every command supports \`--json\`. If setup fails, run \`$CLI_DIR/gads auth setup\`.
ENDSKILL
  ok "Skill → $dir/SKILL.md"
}

# ── Hook template ────────────────────────────────────────────
write_hook() {
  local hookdir="$1" settings="$2"
  mkdir -p "$hookdir"
  cat > "$hookdir/gads-update-check.js" << ENDHOOK
// gads-cli — update check on session start
const { execSync } = require("child_process");
try {
  const r = execSync("git -C $CLI_DIR fetch --dry-run 2>&1", { encoding: "utf-8", timeout: 5000 });
  if (r.trim()) process.stderr.write("\\x1b[33m⚠ gads-cli has updates. Run: git -C $CLI_DIR pull\\x1b[0m\\n");
} catch (e) {}
ENDHOOK
  ok "Hook → $hookdir/gads-update-check.js"

  # Wire into settings.json
  if [[ -n "$settings" && -f "$settings" ]]; then
    if ! grep -q "gads-update-check" "$settings" 2>/dev/null; then
      $PY -c "
import json
p = '$settings'
s = json.load(open(p))
h = s.setdefault('hooks', {})
ss = h.setdefault('SessionStart', [])
ss.append({'hooks': [{'type': 'command', 'command': 'node \"$hookdir/gads-update-check.js\"'}]})
json.dump(s, open(p, 'w'), indent=4)
" 2>/dev/null && ok "Hook wired → $settings" || warn "Wire hook manually into $settings"
    else
      ok "Hook already in settings"
    fi
  fi
}

# ── Install per platform ─────────────────────────────────────
install_for() {
  local platform="$1" agent_dir="$2" skill_dir="$3" hook_dir="${4:-}" settings="${5:-}"

  if [[ -t 0 ]]; then
    [[ "$(prompt "Install for $platform?" "Y/n")" =~ ^[Nn] ]] && return
  fi

  echo ""
  echo -e "  ${B}${platform}${R}"
  write_agent "$agent_dir"
  [[ -n "$skill_dir" ]] && write_skill "$skill_dir" || true
  [[ -n "$hook_dir" ]] && write_hook "$hook_dir" "$settings" || true
}

if $HAS_CLAUDE; then
  if [[ "$SCOPE" == "global" ]]; then
    install_for "Claude Code" "$HOME/.claude/agents" "$HOME/.claude/skills" "$HOME/.claude/hooks" "$HOME/.claude/settings.json"
  else
    install_for "Claude Code" ".claude/agents" ".claude/skills" ".claude/hooks" ""
  fi
fi

if $HAS_GSD; then
  if [[ "$SCOPE" == "global" ]]; then
    install_for "gsd-pi" "$HOME/.gsd/agent/agents" "$HOME/.gsd/agent/skills" "" ""
  else
    install_for "gsd-pi" ".gsd/agents" ".gsd/skills" "" ""
  fi
fi

if $HAS_RUFLO; then
  if [[ "$SCOPE" == "global" ]]; then
    install_for "ruflo" "$HOME/.ruflo/agents" "" "" ""
  else
    install_for "ruflo" ".ruflo/agents" "" "" ""
  fi
fi

# ── Step 6: Auth ─────────────────────────────────────────────
step 6 6 "Credentials"

ENV_FILE="$CLI_DIR/.env"
if [[ ! -f "$ENV_FILE" && -f "$CLI_DIR/.env.example" ]]; then
  cp "$CLI_DIR/.env.example" "$ENV_FILE"
  ok "Created .env from template"
elif [[ -f "$ENV_FILE" ]]; then
  ok ".env exists"
fi

if ! $SKIP_AUTH && [[ -t 0 ]]; then
  if [[ "$(prompt "Run auth setup now?" "Y/n")" =~ ^[Yy] ]]; then
    echo ""
    PYTHONPATH="$CLI_DIR" $PY "$CLI_DIR/gads" auth setup
  else
    echo "  Run later: $CLI_DIR/gads auth setup"
  fi
else
  echo "  Run: $CLI_DIR/gads auth setup"
fi

# ── Done ─────────────────────────────────────────────────────
echo ""
echo -e "  ${CG}╔══════════════════════════════════════════════════════╗${R}"
echo -e "  ${CG}║${R}  ${B}Installation complete!${R}                              ${CG}║${R}"
echo -e "  ${CG}╚══════════════════════════════════════════════════════╝${R}"
echo ""
echo "  CLI:       $CLI_DIR/gads"
echo "  Verify:    $CLI_DIR/gads doctor"
echo "  API test:  $CLI_DIR/gads auth test"
echo "  Help:      $CLI_DIR/gads --help"
echo ""
echo -e "  ${D}Update:     git -C $CLI_DIR pull${R}"
echo -e "  ${D}Reinstall:  re-run this script${R}"
echo -e "  ${D}Uninstall:  rm -rf $CLI_DIR${R}"
echo ""
