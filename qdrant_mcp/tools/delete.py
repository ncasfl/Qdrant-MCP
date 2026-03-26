"""Delete tool — qdrant_delete."""

import asyncio
import json
import logging
from typing import Optional

from mcp.server.fastmcp import Context

from ..server import mcp, AppContext

# Import RAG lib modules (available via PYTHONPATH)
from rag.lib.store import delete_source, delete_points, collection_stats

log = logging.getLogger("qdrant_mcp.delete")


@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def qdrant_delete(
    collection: str,
    confirm: bool,
    point_ids: Optional[list[str]] = None,
    filter_source: Optional[str] = None,
    ctx: Context = None,
) -> str:
    """Remove points from a Qdrant collection by point IDs or source filter.

    At least one of point_ids or filter_source must be provided.
    The confirm parameter must be true to execute — this is a safety gate
    for destructive operations.

    Args:
        collection: Qdrant collection name.
        confirm: Must be true to execute deletion. Safety gate.
        point_ids: Specific point IDs (UUIDs) to delete.
        filter_source: Delete all points matching this source file path.
    """
    if not confirm:
        return "Error: confirm must be true to execute deletion. This is a destructive operation."

    if not point_ids and not filter_source:
        return "Error: at least one of point_ids or filter_source must be provided."

    app: AppContext = ctx.request_context.lifespan_context
    client = app.qdrant

    # Get point count before deletion
    try:
        stats_before = await asyncio.to_thread(collection_stats, client, collection=collection)
    except Exception as e:
        log.error("Failed to get collection stats for '%s': %s", collection, e)
        return f"Error: cannot access collection '{collection}' — {e}"

    if stats_before["status"] == "not_found":
        return f"Error: collection '{collection}' not found."

    points_before = stats_before["points"]

    # Execute deletion(s)
    try:
        if filter_source:
            await ctx.info(f"Deleting points with source='{filter_source}'...")
            await asyncio.to_thread(delete_source, client, filter_source, collection=collection)

        if point_ids:
            await ctx.info(f"Deleting {len(point_ids)} point(s) by ID...")
            await asyncio.to_thread(delete_points, client, point_ids, collection=collection)
    except Exception as e:
        log.error("Deletion failed on '%s': %s", collection, e)
        return f"Error: deletion failed — {e}"

    # Get point count after deletion
    stats_after = await asyncio.to_thread(collection_stats, client, collection=collection)
    points_after = stats_after["points"]
    points_deleted = points_before - points_after

    log.info("Deleted %d points from '%s' (source=%s, ids=%s)",
             points_deleted, collection, filter_source,
             len(point_ids) if point_ids else 0)

    result = {
        "status": "ok",
        "collection": collection,
        "points_before": points_before,
        "points_after": points_after,
        "points_deleted": points_deleted,
    }

    if filter_source:
        result["filter_source"] = filter_source
    if point_ids:
        result["point_ids_requested"] = len(point_ids)

    return json.dumps(result, indent=2)
