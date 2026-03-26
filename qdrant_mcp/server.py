"""Qdrant MCP Server — FastMCP server with lifespan-managed Qdrant client."""

import logging
import sys
from contextlib import asynccontextmanager
from dataclasses import dataclass

from qdrant_client import QdrantClient

from mcp.server.fastmcp import FastMCP

from . import config

# ── Logging ───────────────────────────────────────────────────────────────

log = logging.getLogger("qdrant_mcp")


def setup_logging(transport: str = "stdio") -> None:
    """Configure logging. stderr for stdio (keeps stdout clean for MCP), file for HTTP."""
    handler: logging.Handler
    if transport == "stdio":
        handler = logging.StreamHandler(sys.stderr)
    else:
        try:
            handler = logging.FileHandler(
                f"{config.LOG_FILE}", mode="a", encoding="utf-8"
            )
        except OSError:
            handler = logging.StreamHandler(sys.stderr)

    handler.setFormatter(logging.Formatter(
        "%(asctime)s  %(levelname)-5s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root = logging.getLogger("qdrant_mcp")
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


# ── Lifespan ──────────────────────────────────────────────────────────────


@dataclass
class AppContext:
    """Shared state available to all tools via server.get_context()."""
    qdrant: QdrantClient


@asynccontextmanager
async def lifespan(server: FastMCP):
    """Initialize Qdrant client on startup, close on shutdown."""
    client = QdrantClient(host=config.QDRANT_HOST, port=config.QDRANT_PORT)
    try:
        collections = client.get_collections()
        log.info(
            "Connected to Qdrant at %s (%d collections)",
            config.QDRANT_URL, len(collections.collections),
        )
        yield AppContext(qdrant=client)
    except Exception as e:
        log.error("Failed to connect to Qdrant at %s: %s", config.QDRANT_URL, e)
        raise
    finally:
        client.close()
        log.info("Qdrant client closed")


# ── Server ────────────────────────────────────────────────────────────────

mcp = FastMCP(
    name="qdrant_mcp",
    instructions=(
        "Qdrant MCP Server — semantic search, document ingestion, and collection "
        "management over ai-beast's Qdrant vector store with GPU-accelerated embeddings."
    ),
    host=config.MCP_HTTP_HOST,
    port=config.MCP_HTTP_PORT,
    lifespan=lifespan,
    log_level="INFO",
)

# ── Register tools (import triggers @mcp.tool() decorators) ──────────────

from .tools import collections  # noqa: E402, F401
from .tools import search  # noqa: E402, F401
from .tools import ingest  # noqa: E402, F401
from .tools import delete  # noqa: E402, F401
