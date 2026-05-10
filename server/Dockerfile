FROM python:3.12-slim

WORKDIR /app
RUN pip install --no-cache-dir uv

# claude-agent-sdk needs the claude CLI on PATH. Install via npm (Node is
# the official distribution channel). ~50 MB; only used when
# CHAT_BACKEND=agent_sdk - prod compose leaves the binary idle.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g @anthropic-ai/claude-code \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy source first so editable install can locate the whiteboard_mcp package.
COPY pyproject.toml ./
COPY whiteboard_mcp ./whiteboard_mcp
# bank/ is imported by whiteboard_mcp.server at boot (ingest_bank, seed JSONs).
# bank/generated/ holds the 75 generated question files; bank/seed/ holds the
# topic taxonomy + prereq DAG. Both are needed at runtime.
COPY bank ./bank

RUN uv pip install --system -e .

# claude CLI refuses --dangerously-skip-permissions under root. Drop to a
# non-root user (uid 1000) so the agent_sdk evaluator backend can spawn
# the CLI without that guard tripping. /app/data is the bind-mounted DB
# volume; chown so the runtime user can write coach.db.
RUN useradd --uid 1000 --create-home --shell /bin/bash app \
    && mkdir -p /app/data \
    && chown -R app:app /app
USER app

EXPOSE 8000
CMD ["python", "-m", "whiteboard_mcp.server"]
