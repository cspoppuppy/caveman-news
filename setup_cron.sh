#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$REPO_DIR/logs"
CRON_MARKER="caveman-news"

# Resolve absolute path to uv
UV_PATH="$(which uv 2>/dev/null || echo "")"
if [[ -z "$UV_PATH" ]]; then
    echo "❌ Error: 'uv' not found in PATH. Install it first: https://docs.astral.sh/uv/"
    exit 1
fi

# Create logs dir (it's gitignored — must exist at runtime)
mkdir -p "$LOG_DIR"

# Build the cron line — delegates to run.sh which handles SSH env setup
CRON_LINE="30 9 * * * \"$REPO_DIR/run.sh\" >> \"$LOG_DIR/cron.log\" 2>&1"

# Idempotency check — skip if already installed
if crontab -l 2>/dev/null | grep -q "$CRON_MARKER"; then
    echo "✅ Cron job already installed. Nothing to do."
    crontab -l | grep "$CRON_MARKER"
    exit 0
fi

# Install — use || true so set -e doesn't exit on empty crontab (crontab -l returns exit 1 when empty)
(crontab -l 2>/dev/null || true; echo "$CRON_LINE") | crontab -

# Verify installation
if crontab -l 2>/dev/null | grep -q "$CRON_MARKER"; then
    echo "✅ Cron job installed successfully:"
    crontab -l | grep "$CRON_MARKER"
else
    echo "❌ Installation failed — cron entry not found after install"
    exit 1
fi
