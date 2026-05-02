FROM python:3.12-slim

WORKDIR /app
RUN pip install --no-cache-dir uv

# Copy source first so editable install can locate the whiteboard_mcp package.
COPY pyproject.toml ./
COPY whiteboard_mcp ./whiteboard_mcp

RUN uv pip install --system -e .

EXPOSE 8000
CMD ["python", "-m", "whiteboard_mcp.server"]
