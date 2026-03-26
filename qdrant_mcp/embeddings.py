"""Embedding abstraction — OpenAI-compatible /v1/embeddings API.

Works with any provider that implements the OpenAI embeddings format:
  - Ollama (http://localhost:11434/v1)
  - llama-server / llama.cpp (http://localhost:8080/v1)
  - OpenAI (https://api.openai.com/v1)
  - Azure OpenAI, Together, Fireworks, etc.

Configure via config.py or environment variables:
  EMBED_BASE_URL  — API base URL (default: http://localhost:11434/v1)
  EMBED_MODEL     — model name (default: nomic-embed-text)
  EMBED_API_KEY   — optional API key (default: none)
"""

import json
import logging
import os
import urllib.request
from typing import Optional

from . import config

log = logging.getLogger("qdrant_mcp.embeddings")

# Resolve config with env var overrides
_BASE_URL = os.environ.get("EMBED_BASE_URL", config.EMBED_BASE_URL).rstrip("/")
_MODEL = os.environ.get("EMBED_MODEL", config.EMBED_MODEL)
_API_KEY = os.environ.get("EMBED_API_KEY", config.EMBED_API_KEY)
_BATCH_SIZE = 64

# Prefixes for asymmetric embedding models (e.g. nomic-embed-text).
# Set to empty strings if your model doesn't use prefixes.
_QUERY_PREFIX = os.environ.get("EMBED_QUERY_PREFIX", config.EMBED_QUERY_PREFIX)
_DOCUMENT_PREFIX = os.environ.get("EMBED_DOCUMENT_PREFIX", config.EMBED_DOCUMENT_PREFIX)


def _call_embeddings(texts: list[str]) -> list[list[float]]:
    """Call the OpenAI-compatible /v1/embeddings endpoint."""
    url = f"{_BASE_URL}/embeddings"
    headers = {"Content-Type": "application/json"}
    if _API_KEY:
        headers["Authorization"] = f"Bearer {_API_KEY}"

    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i : i + _BATCH_SIZE]
        payload = json.dumps({"model": _MODEL, "input": batch}).encode()
        req = urllib.request.Request(url, data=payload, headers=headers)
        resp = urllib.request.urlopen(req, timeout=300)
        result = json.loads(resp.read())

        # OpenAI format: {"data": [{"embedding": [...], "index": 0}, ...]}
        # Sort by index to guarantee order
        sorted_data = sorted(result["data"], key=lambda d: d["index"])
        all_embeddings.extend(d["embedding"] for d in sorted_data)

    return all_embeddings


def embed_texts(
    texts: list[str],
    prefix: Optional[str] = None,
) -> list[list[float]]:
    """Embed a list of texts for document storage.

    Args:
        texts: List of strings to embed.
        prefix: Optional prefix prepended to each text before embedding.
                Defaults to EMBED_DOCUMENT_PREFIX from config.

    Returns:
        List of embedding vectors, one per input text.
    """
    if prefix is None:
        prefix = _DOCUMENT_PREFIX

    if prefix:
        texts = [prefix + t for t in texts]

    log.debug("Embedding %d texts via %s (model=%s)", len(texts), _BASE_URL, _MODEL)
    return _call_embeddings(texts)


def embed_query(query: str) -> list[float]:
    """Embed a single search query.

    Uses EMBED_QUERY_PREFIX to distinguish queries from documents
    (important for asymmetric models like nomic-embed-text).

    Args:
        query: Search query string.

    Returns:
        Single embedding vector.
    """
    text = (_QUERY_PREFIX + query) if _QUERY_PREFIX else query
    log.debug("Embedding query via %s (model=%s)", _BASE_URL, _MODEL)
    return _call_embeddings([text])[0]
