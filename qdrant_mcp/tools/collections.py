"""Collection browsing tools — list_collections and collection_info."""

import asyncio
import json
import logging
from typing import Literal

from mcp.server.fastmcp import Context

from ..server import mcp, AppContext

log = logging.getLogger("qdrant_mcp.collections")


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def qdrant_list_collections(
    response_format: Literal["markdown", "json"] = "markdown",
    ctx: Context = None,
) -> str:
    """List all collections in Qdrant with point counts, vector dimensions, and distance metrics."""
    app: AppContext = ctx.request_context.lifespan_context
    client = app.qdrant

    try:
        collections_resp = await asyncio.to_thread(client.get_collections)
    except Exception as e:
        log.error("Failed to list collections: %s", e)
        return f"Error: cannot reach Qdrant — {e}"

    results = []
    for col in collections_resp.collections:
        try:
            info = await asyncio.to_thread(client.get_collection, col.name)
        except Exception as e:
            log.warning("Failed to get info for collection '%s': %s", col.name, e)
            results.append({"name": col.name, "points": "?", "dimension": "?", "distance": "?"})
            continue

        vec_cfg = info.config.params.vectors
        if hasattr(vec_cfg, "size"):
            dim = vec_cfg.size
            distance = str(vec_cfg.distance)
        elif isinstance(vec_cfg, dict):
            first = next(iter(vec_cfg.values()))
            dim = first.size
            distance = str(first.distance)
        else:
            dim = "unknown"
            distance = "unknown"

        results.append({
            "name": col.name,
            "points": info.points_count,
            "dimension": dim,
            "distance": distance,
        })

    if response_format == "json":
        return json.dumps(results, indent=2)

    if not results:
        return "No collections found in Qdrant."

    lines = [f"**Qdrant Collections** ({len(results)} total)\n"]
    lines.append("| Collection | Points | Dimension | Distance |")
    lines.append("|------------|--------|-----------|----------|")
    for r in results:
        lines.append(f"| {r['name']} | {r['points']} | {r['dimension']} | {r['distance']} |")
    return "\n".join(lines)


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def qdrant_collection_info(
    collection: str,
    response_format: Literal["markdown", "json"] = "markdown",
    ctx: Context = None,
) -> str:
    """Get detailed info on a specific Qdrant collection: vector config, point count, index status, and segments."""
    app: AppContext = ctx.request_context.lifespan_context
    client = app.qdrant

    try:
        info = await asyncio.to_thread(client.get_collection, collection)
    except Exception as e:
        log.error("Failed to get collection '%s': %s", collection, e)
        return f"Error: collection '{collection}' not found — {e}"

    vec_cfg = info.config.params.vectors
    if hasattr(vec_cfg, "size"):
        vec_info = {
            "dimension": vec_cfg.size,
            "distance": str(vec_cfg.distance),
        }
    elif isinstance(vec_cfg, dict):
        vec_info = {
            name: {"dimension": v.size, "distance": str(v.distance)}
            for name, v in vec_cfg.items()
        }
    else:
        vec_info = {"raw": str(vec_cfg)}

    result = {
        "collection": collection,
        "points": info.points_count,
        "vectors": vec_info,
        "status": str(info.status),
        "segments": info.segments_count,
        "indexed_vectors": info.indexed_vectors_count,
        "optimizer_status": str(info.optimizer_status),
    }

    if response_format == "json":
        return json.dumps(result, indent=2)

    lines = [
        f"**Collection: {collection}**\n",
        f"- **Points**: {result['points']}",
        f"- **Status**: {result['status']}",
        f"- **Segments**: {result['segments']}",
        f"- **Indexed vectors**: {result['indexed_vectors']}",
        f"- **Optimizer**: {result['optimizer_status']}",
        "",
        "**Vector config**:",
    ]
    if isinstance(vec_info, dict) and "dimension" in vec_info:
        lines.append(f"- Dimension: {vec_info['dimension']}")
        lines.append(f"- Distance: {vec_info['distance']}")
    else:
        for k, v in vec_info.items():
            lines.append(f"- {k}: {v}")

    return "\n".join(lines)
