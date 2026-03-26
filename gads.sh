#!/usr/bin/env bash
# Wrapper to run gads CLI with .env loaded.
# Usage: ./gads.sh query "SELECT campaign.name FROM campaign"
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$DIR/.env" ]; then
    set -a; source "$DIR/.env"; set +a
fi
exec python3 "$DIR/gads" "$@"
