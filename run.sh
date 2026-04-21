#!/usr/bin/env bash
# Fetch AI news, summarise, commit, and push to GitHub.
# Safe to run manually or via cron.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$REPO_DIR/logs"
UV_PATH="$(which uv 2>/dev/null || echo "$HOME/.local/bin/uv")"

mkdir -p "$LOG_DIR"

# Load SSH key agent socket if available (needed in cron — macOS Keychain)
if [[ -z "${SSH_AUTH_SOCK:-}" ]]; then
    SSH_SOCK_CANDIDATE="$HOME/.ssh/ssh_auth_sock"
    [[ -S "$SSH_SOCK_CANDIDATE" ]] && export SSH_AUTH_SOCK="$SSH_SOCK_CANDIDATE"
fi

# Ensure git can find ssh on macOS
export PATH="/usr/bin:/usr/local/bin:$PATH"

cd "$REPO_DIR"
"$UV_PATH" run python -m aggregator

# Commit and push everything — content + any code changes
if [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then
    TODAY=$(date -u +%Y-%m-%d)
    git add -A
    git commit -m "🪨 caveman news ${TODAY}"
    git push
else
    echo "No changes — nothing to push."
fi
