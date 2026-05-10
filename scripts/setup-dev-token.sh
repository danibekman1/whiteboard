#!/usr/bin/env bash
# Generate a Claude Code OAuth token (one-time setup, ~1 minute) and
# write it into .env so the dev backend (CHAT_BACKEND=agent_sdk) picks
# it up.
#
# What it does:
#   1. Builds the dev web image so we can borrow its `claude` CLI - no
#      need for the user to install Node or Claude Code on the host.
#   2. Runs `claude setup-token` interactively inside that image. The
#      claude CLI prints a URL the user opens in their browser, the
#      user authorizes against their own Claude account, and the token
#      lands on stdout.
#   3. Captures the token, writes CHAT_BACKEND + CLAUDE_CODE_OAUTH_TOKEN
#      to .env (replacing any prior values).
#
# Prerequisite: a Claude Code Team / Pro / Max subscription. The OAuth
# flow goes through the user's own account; the token bills to that
# account, not to whoever shipped this repo.
set -euo pipefail
cd "$(dirname "$0")/.."

ENV_FILE=".env"
[[ -f "$ENV_FILE" ]] || cp .env.example "$ENV_FILE"

if grep -qE '^CLAUDE_CODE_OAUTH_TOKEN=(oat-|sk-ant-oat)' "$ENV_FILE"; then
  echo "Token already set in $ENV_FILE."
  echo "Delete the CLAUDE_CODE_OAUTH_TOKEN line and re-run to refresh."
  exit 0
fi

echo "Building web image (one-time, ~2 min on cold cache)..."
docker compose -f docker-compose.yml -f docker-compose.dev.yml build web >/dev/null

echo
echo "Running 'claude setup-token' in a container."
echo "  - A URL will appear; open it in your browser."
echo "  - Authorize with your Claude Code Team / Pro / Max account."
echo "  - Paste the auth code back when prompted."
echo

# --no-deps skips starting the server. Clear any inherited token so the
# CLI runs the OAuth flow regardless of compose env wiring.
TOKEN=$(
  docker compose -f docker-compose.yml -f docker-compose.dev.yml \
    run --rm --no-deps \
    -e CLAUDE_CODE_OAUTH_TOKEN= \
    web claude setup-token \
    | tee /dev/tty \
    | tail -1 \
    | tr -d '\r\n'
)

if [[ ! "$TOKEN" =~ ^(oat-|sk-ant-oat) ]]; then
  echo
  echo "ERROR: did not capture a valid OAuth token from setup-token output." >&2
  echo "Last line read: '$TOKEN'" >&2
  echo "Try running setup manually: 'docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm --no-deps web claude setup-token'" >&2
  exit 1
fi

# sed -i.bak is portable across BSD and GNU sed; remove the .bak after.
sed -i.bak '/^CHAT_BACKEND=/d;/^CLAUDE_CODE_OAUTH_TOKEN=/d' "$ENV_FILE"
rm -f "$ENV_FILE.bak"
{ echo "CHAT_BACKEND=agent_sdk"; echo "CLAUDE_CODE_OAUTH_TOKEN=$TOKEN"; } >> "$ENV_FILE"

echo
echo "✓ Wrote CHAT_BACKEND=agent_sdk and CLAUDE_CODE_OAUTH_TOKEN to $ENV_FILE."
echo
echo "Now boot the dev stack:"
echo "  docker compose -f docker-compose.yml -f docker-compose.dev.yml up"
