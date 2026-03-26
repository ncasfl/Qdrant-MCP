"""Semantic search tool — qdrant_search."""

import asyncio
import json
import logging
import os
from typing import Literal, Optional
from urllib.error import URLError

from mcp.server.fastmcp import Context

from ..server import mcp, AppContext
from ..embeddings import embed_query

# Import RAG lib modules (available via PYTHONPATH)
from rag.lib.store import search as qdrant_search_fn

log = logging.getLogger("qdrant_mcp.search")


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def qdrant_search(
    query: str,
    collection: str = "documents",
    limit: int = 5,
    score_threshold: Optional[float] = None,
    source_filter: Optional[str] = None,
    response_format: Literal["markdown", "json"] = "markdown",
    ctx: Context = None,
) -> str:
    """Semantic search over ingested documents in Qdrant.

    Embeds the query via GPU (nomic-embed-text on Ollama), then searches the
    specified collection. Returns ranked results with text, source file,
    page number, chunk index, and similarity score.

    Args:
        query: Natural language search query.
        collection: Qdrant collection name (default: "documents").
        limit: Max results to return (1-20, default: 5).
        score_threshold: Minimum similarity score (0.0-1.0). Results below this are filtered out.
        source_filter: Restrict search to a specific source file path.
        response_format: "markdown" for human-readable or "json" for structured output.
    """
    if not 1 <= limit <= 20:
        return "Error: limit must be between 1 and 20."

    if score_threshold is not None and not 0.0 <= score_threshold <= 1.0:
        return "Error: score_threshold must be between 0.0 and 1.0."

    app: AppContext = ctx.request_context.lifespan_context
    client = app.qdrant

    # Embed query on GPU via Ollama
    await ctx.info(f"Embedding query: {query[:80]}...")
    try:
        query_vector = await asyncio.to_thread(embed_query, query)
    except URLError as e:
        log.error("Ollama embedding failed: %s", e)
        return "Error: Ollama is not reachable (embedding failed). Is it running on port 11434?"
    except Exception as e:
        log.error("Embedding failed: %s", e)
        return f"Error: embedding failed — {e}"

    # Search Qdrant
    await ctx.info(f"Searching collection '{collection}'...")
    try:
        results = await asyncio.to_thread(
            qdrant_search_fn,
            client,
            query_vector=query_vector,
            limit=limit,
            source_filter=source_filter,
            collection=collection,
        )
    except Exception as e:
        log.error("Qdrant search failed on '%s': %s", collection, e)
        return f"Error: search failed on collection '{collection}' — {e}"

    # Apply score_threshold post-filter
    if score_threshold is not None:
        results = [r for r in results if r.score >= score_threshold]

    if not results:
        return f"No results found for: {query}"

    if response_format == "json":
        output = [
            {
                "score": round(r.score, 4),
                "source": r.source,
                "page": r.page,
                "chunk_index": r.chunk_index,
                "text": r.text,
            }
            for r in results
        ]
        return json.dumps(output, indent=2)

    # Markdown format
    lines = [f"**Search results for:** {query}\n"]
    lines.append(f"Collection: `{collection}` | Results: {len(results)}")
    if source_filter:
        lines.append(f"Filtered to: `{source_filter}`")
    if score_threshold is not None:
        lines.append(f"Score threshold: {score_threshold}")
    lines.append("")

    for i, r in enumerate(results, 1):
        source_name = os.path.basename(r.source)
        page_str = f" p.{r.page}" if r.page else ""
        lines.append(f"### [{i}] {r.score:.4f} — {source_name}{page_str} (chunk {r.chunk_index})")
        lines.append("")
        # Truncate very long chunks for readability
        text = r.text if len(r.text) <= 800 else r.text[:800] + "..."
        lines.append(text)
        lines.append("")

    return "\n".join(lines)
