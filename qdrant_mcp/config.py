"""Configuration constants for qdrant_mcp server."""

# Qdrant vector store
QDRANT_URL = "http://localhost:6333"
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333

# Embedding provider — OpenAI-compatible /v1/embeddings API
# Works with: Ollama, llama-server, OpenAI, Azure, Together, Fireworks, etc.
# Override with environment variables: EMBED_BASE_URL, EMBED_MODEL, EMBED_API_KEY
EMBED_BASE_URL = "http://localhost:11434/v1"  # Ollama default
EMBED_MODEL = "nomic-embed-text"
EMBED_API_KEY = ""  # Set via EMBED_API_KEY env var for OpenAI/cloud providers
EMBED_DIMENSION = 768

# Prefixes for asymmetric embedding models (e.g. nomic-embed-text).
# These are prepended client-side before calling the API.
# Set to "" if your model doesn't use prefixes.
EMBED_QUERY_PREFIX = "search_query: "
EMBED_DOCUMENT_PREFIX = "search_document: "

# Collection defaults
DEFAULT_COLLECTION = "documents"
DEFAULT_CHUNK_SIZE = 512
DEFAULT_CHUNK_OVERLAP = 64

# MCP HTTP transport
MCP_HTTP_HOST = "0.0.0.0"
MCP_HTTP_PORT = 8090

# Logging
LOG_FILE = "/home/chohman/logs/qdrant-mcp.log"

# Security: allowed paths for file ingestion
ALLOWED_INGEST_PATHS = [
    "/home/chohman/",
    "/mnt/hdd/",
]
