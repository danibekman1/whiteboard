"""FastMCP server entry point. v0 stub - tools wired in later tasks."""
from __future__ import annotations
import logging

from fastmcp import FastMCP

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
mcp = FastMCP("whiteboard-mcp")


def main() -> None:
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000, path="/mcp")


if __name__ == "__main__":
    main()
