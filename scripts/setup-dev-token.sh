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
#      user authorizes against their own Claude account, pastes the
#      resulting auth code back into the CLI, and the CLI prints the
#      final OAuth token.
#   3. Prompts the user to paste that token; writes CHAT_BACKEND and
#      CLAUDE_CODE_OAUTH_TOKEN to .env (replacing any prior values).
#
# Why a two-step prompt instead of auto-capture:
#   The earlier version captured the token via `| tee /dev/tty | tail -1`.
#   That pipe made the claude CLI see non-TTY stdout, which caused it to
#   buffer output - so the URL did not appear in the user's terminal
#   until claude was already done. A targeted PTY workaround (`script`,
#   `unbuffer`, named pipes) is fragile across distros. A direct `docker
#   compose run` (no pipe) keeps claude unbuffered and interactive; the
#   user paste step is the cost of that simplicity.
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
echo "  1. A URL will appear; open it in your browser."
echo "  2. Authorize with your Claude Code Team / Pro / Max account."
echo "  3. Paste the auth code from the browser back into the CLI."
echo "  4. Claude prints a final token (starts with 'oat-' or 'sk-ant-oat-')."
echo "  5. Copy that token; this script will prompt you to paste it below."
echo

# Run setup-token interactively, NO pipe. Piping caused claude to buffer
# stdout until completion, hiding the URL during the OAuth flow. The
# inherited CLAUDE_CODE_OAUTH_TOKEN is cleared so the CLI always runs the
# OAuth flow regardless of compose env wiring. --no-deps skips starting
# the server (no point spinning it up just to do auth).
docker compose -f docker-compose.yml -f docker-compose.dev.yml \
  run --rm --no-deps \
  -e CLAUDE_CODE_OAUTH_TOKEN= \
  web claude setup-token

echo
read -rp "Paste the token printed above: " TOKEN
echo

if [[ ! "$TOKEN" =~ ^(oat-|sk-ant-oat-)[A-Za-z0-9_-]+$ ]]; then
  echo "ERROR: token must start with 'oat-' or 'sk-ant-oat-' and contain only [A-Za-z0-9_-]." >&2
  echo "Got: ${TOKEN:0:8}... (${#TOKEN} chars). Aborting without modifying $ENV_FILE." >&2
  exit 1
fi

# sed -i.bak is portable across BSD and GNU sed; remove the .bak after.
sed -i.bak '/^CHAT_BACKEND=/d;/^CLAUDE_CODE_OAUTH_TOKEN=/d' "$ENV_FILE"
rm -f "$ENV_FILE.bak"
{ echo "CHAT_BACKEND=agent_sdk"; echo "CLAUDE_CODE_OAUTH_TOKEN=$TOKEN"; } >> "$ENV_FILE"

echo
echo "Wrote CHAT_BACKEND=agent_sdk and CLAUDE_CODE_OAUTH_TOKEN to $ENV_FILE."
echo
echo "Now boot the dev stack:"
echo "  docker compose -f docker-compose.yml -f docker-compose.dev.yml up"
