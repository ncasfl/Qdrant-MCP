"""Ingest tools — qdrant_ingest_text and qdrant_ingest_file."""

import asyncio
import json
import logging
import os
from typing import Literal, Optional
from urllib.error import URLError

from mcp.server.fastmcp import Context

from ..server import mcp, AppContext
from .. import config
from ..embeddings import embed_texts

# Import RAG lib modules (available via PYTHONPATH)
from rag.lib.chunker import chunk_text
from rag.lib.extract import extract
from rag.lib.store import ensure_collection, upsert_chunks

log = logging.getLogger("qdrant_mcp.ingest")


def _chunks_to_dicts(chunks) -> list[dict]:
    """Convert Chunk dataclass objects to dicts for store.upsert_chunks()."""
    return [
        {"text": c.text, "index": c.index, "page": c.page, "char_offset": c.char_offset}
        for c in chunks
    ]


def _validate_path(file_path: str) -> str | None:
    """Validate file path against allowed directories. Returns error message or None."""
    abs_path = os.path.abspath(file_path)
    for allowed in config.ALLOWED_INGEST_PATHS:
        if abs_path.startswith(allowed):
            return None
    return (
        f"Error: path '{abs_path}' is outside allowed directories. "
        f"Allowed: {config.ALLOWED_INGEST_PATHS}"
    )


@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    }
)
async def qdrant_ingest_text(
    text: str,
    source: str,
    collection: str = "documents",
    chunk_size: int = 512,
    chunk_overlap: int = 64,
    metadata: Optional[dict] = None,
    ctx: Context = None,
) -> str:
    """Chunk, embed (GPU), and store raw text in Qdrant.

    Splits the text into overlapping chunks, embeds each via Ollama GPU
    (nomic-embed-text), and upserts into the specified collection.
    Uses deterministic point IDs based on source + chunk index, so
    re-ingesting the same source overwrites previous chunks.

    Args:
        text: The text content to ingest.
        source: Source identifier (e.g. filename, URL, label). Used for
                filtering and deduplication.
        collection: Target Qdrant collection (default: "documents").
        chunk_size: Target chunk size in words (100-2000, default: 512).
        chunk_overlap: Overlap between chunks in words (0-500, default: 64).
        metadata: Optional additional key-value metadata to attach to each point.
    """
    if not text.strip():
        return "Error: text is empty."

    if not 100 <= chunk_size <= 2000:
        return "Error: chunk_size must be between 100 and 2000."

    if not 0 <= chunk_overlap <= 500:
        return "Error: chunk_overlap must be between 0 and 500."

    if chunk_overlap >= chunk_size:
        return "Error: chunk_overlap must be less than chunk_size."

    app: AppContext = ctx.request_context.lifespan_context
    client = app.qdrant

    # Ensure collection exists
    try:
        await asyncio.to_thread(ensure_collection, client, collection=collection)
    except Exception as e:
        log.error("Failed to ensure collection '%s': %s", collection, e)
        return f"Error: cannot access Qdrant collection '{collection}' — {e}"

    # Chunk
    await ctx.info(f"Chunking text ({len(text)} chars, chunk_size={chunk_size})...")
    chunks = await asyncio.to_thread(
        chunk_text, text, chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )

    if not chunks:
        return "Error: text produced no chunks after splitting."

    # Embed on GPU
    await ctx.info(f"Embedding {len(chunks)} chunks via GPU...")
    try:
        texts = [c.text for c in chunks]
        vectors = await asyncio.to_thread(embed_texts, texts)
    except URLError as e:
        log.error("Ollama embedding failed: %s", e)
        return "Error: Ollama is not reachable (embedding failed). Is it running on port 11434?"
    except Exception as e:
        log.error("Embedding failed for source '%s': %s", source, e)
        return f"Error: embedding failed — {e}"

    # Upsert into Qdrant
    await ctx.info(f"Upserting {len(chunks)} points into '{collection}'...")
    try:
        chunk_dicts = _chunks_to_dicts(chunks)
        n_upserted = await asyncio.to_thread(
            upsert_chunks, client, chunk_dicts, vectors, source, collection=collection
        )
    except Exception as e:
        log.error("Qdrant upsert failed for source '%s': %s", source, e)
        return f"Error: failed to store chunks in Qdrant — {e}"

    log.info("Ingested text source='%s' chunks=%d collection='%s'", source, len(chunks), collection)

    result = {
        "status": "ok",
        "source": source,
        "collection": collection,
        "chunks_created": len(chunks),
        "points_upserted": n_upserted,
        "text_length": len(text),
    }

    return json.dumps(result, indent=2)


@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    }
)
async def qdrant_ingest_file(
    file_path: str,
    collection: str = "documents",
    chunk_size: int = 512,
    chunk_overlap: int = 64,
    metadata: Optional[dict] = None,
    ctx: Context = None,
) -> str:
    """Extract text from a PDF or text file, then chunk, embed (GPU), and store in Qdrant.

    Supports PDF (via pymupdf), plain text, markdown, CSV, JSON, log, RST,
    and HTML files. PDF extraction preserves page boundary metadata.

    Args:
        file_path: Absolute path to the file on ai-beast.
        collection: Target Qdrant collection (default: "documents").
        chunk_size: Target chunk size in words (100-2000, default: 512).
        chunk_overlap: Overlap between chunks in words (0-500, default: 64).
        metadata: Optional additional key-value metadata to attach.
    """
    # Validate path security
    path_error = _validate_path(file_path)
    if path_error:
        return path_error

    abs_path = os.path.abspath(file_path)
    if not os.path.isfile(abs_path):
        return f"Error: file not found: {abs_path}"

    if not 100 <= chunk_size <= 2000:
        return "Error: chunk_size must be between 100 and 2000."

    if not 0 <= chunk_overlap <= 500:
        return "Error: chunk_overlap must be between 0 and 500."

    if chunk_overlap >= chunk_size:
        return "Error: chunk_overlap must be less than chunk_size."

    app: AppContext = ctx.request_context.lifespan_context
    client = app.qdrant

    # Ensure collection exists
    try:
        await asyncio.to_thread(ensure_collection, client, collection=collection)
    except Exception as e:
        log.error("Failed to ensure collection '%s': %s", collection, e)
        return f"Error: cannot access Qdrant collection '{collection}' — {e}"

    # Extract text
    await ctx.info(f"Extracting text from {os.path.basename(abs_path)}...")
    try:
        doc = await asyncio.to_thread(extract, abs_path)
    except Exception as e:
        log.error("Text extraction failed for '%s': %s", abs_path, e)
        return f"Error: failed to extract text from {abs_path} — {e}"

    if not doc.text.strip():
        return f"Error: no text extracted from {abs_path}"

    # Chunk
    await ctx.info(f"Chunking {doc.page_count} page(s), {len(doc.text)} chars...")
    chunks = await asyncio.to_thread(
        chunk_text, doc.text,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        pages=doc.pages,
    )

    if not chunks:
        return f"Error: file produced no chunks after splitting: {abs_path}"

    # Embed on GPU
    await ctx.info(f"Embedding {len(chunks)} chunks via GPU...")
    try:
        texts = [c.text for c in chunks]
        vectors = await asyncio.to_thread(embed_texts, texts)
    except URLError as e:
        log.error("Ollama embedding failed: %s", e)
        return "Error: Ollama is not reachable (embedding failed). Is it running on port 11434?"
    except Exception as e:
        log.error("Embedding failed for '%s': %s", abs_path, e)
        return f"Error: embedding failed — {e}"

    # Upsert into Qdrant
    await ctx.info(f"Upserting {len(chunks)} points into '{collection}'...")
    try:
        chunk_dicts = _chunks_to_dicts(chunks)
        n_upserted = await asyncio.to_thread(
            upsert_chunks, client, chunk_dicts, vectors, doc.source, collection=collection
        )
    except Exception as e:
        log.error("Qdrant upsert failed for '%s': %s", abs_path, e)
        return f"Error: failed to store chunks in Qdrant — {e}"

    log.info("Ingested file='%s' pages=%d chunks=%d collection='%s'",
             abs_path, doc.page_count, len(chunks), collection)

    result = {
        "status": "ok",
        "file": abs_path,
        "source": doc.source,
        "collection": collection,
        "pages_extracted": doc.page_count,
        "chunks_created": len(chunks),
        "points_upserted": n_upserted,
        "text_length": len(doc.text),
    }

    return json.dumps(result, indent=2)
