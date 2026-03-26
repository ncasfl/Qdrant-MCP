# qdrant_mcp — Qdrant MCP Server

MCP server exposing Qdrant vector DB store and GPU-accelerated embedding pipeline as tools for Claude Code, Claude.ai, and OpenClaw.

## Tools

| Tool | Description | Annotations |
|------|-------------|-------------|
| `qdrant_search` | Semantic search over ingested documents | read-only, idempotent |
| `qdrant_ingest_text` | Chunk, embed (GPU), and store raw text | write |
| `qdrant_ingest_file` | Extract text from PDF/text files, then ingest | write |
| `qdrant_list_collections` | List all Qdrant collections with stats | read-only, idempotent |
| `qdrant_collection_info` | Detailed info on a specific collection | read-only, idempotent |
| `qdrant_delete` | Remove points by ID or source filter | destructive, requires confirm=true |

## Architecture

```
Clients (stdio / HTTP)
        │
        ▼
  qdrant_mcp (FastMCP)     ← this server
        │
   ┌────┴────┐
   ▼         ▼
Ollama    Qdrant
:11434    :6333
(GPU      (vector
embed)    store)
```

Reuses `~/rag/lib/` modules (chunker, embedder, extractor, store) — no code duplication with the CLI pipeline.

## Running

### Docker (default — used by OpenClaw and Claude.ai)

```bash
~/start-qdrant-mcp.sh          # start sidecar container
~/stop.sh qdrant-mcp            # stop
~/status.sh                     # check status
```

Builds from `Dockerfile`, runs with host networking on port 8090.

### Native (development / debugging)

```bash
~/start-qdrant-mcp.sh --native  # start as Python process
```

Logs to `~/logs/qdrant-mcp.log` (HTTP mode) or stderr (stdio mode).

### Rebuild after code changes

```bash
cd ~/qdrant-mcp && sudo docker compose build
~/stop.sh qdrant-mcp && ~/start-qdrant-mcp.sh
```

## Client Configuration

### Claude Code (stdio)

Configured in `~/.mcp.json`:

```json
{
  "mcpServers": {
    "qdrant": {
      "command": "python3",
      "args": ["-m", "qdrant_mcp", "--transport", "stdio"],
      "cwd": "/home/chohman/qdrant-mcp",
      "env": {
        "PYTHONPATH": "/home/chohman/qdrant-mcp:/home/chohman"
      }
    }
  }
}
```

### Claude.ai (HTTP)

Add as remote MCP server in browser settings:
- URL: `http://192.168.1.16:8090/mcp`

### OpenClaw (HTTP via mcp-remote bridge)

Configured in `~/Dockerz/openclaw/post-configure.sh` via ACPX plugin:

```python
config['plugins']['entries']['acpx']['mcpServers'] = {
    'qdrant': {
        'command': 'npx',
        'args': ['mcp-remote', 'http://127.0.0.1:8090/mcp'],
        'env': {}
    }
}
```

Requires the Docker sidecar running on :8090.

## Configuration

Edit `qdrant_mcp/config.py` or set environment variables:

### Qdrant

| Setting | Default | Description |
|---------|---------|-------------|
| `QDRANT_HOST` | `localhost` | Qdrant server host |
| `QDRANT_PORT` | `6333` | Qdrant REST port |

### Embeddings

Uses any OpenAI-compatible `/v1/embeddings` API. Configure via `config.py` or environment variables.

| Setting | Env Var | Default | Description |
|---------|---------|---------|-------------|
| `EMBED_BASE_URL` | `EMBED_BASE_URL` | `http://localhost:11434/v1` | Embedding API base URL |
| `EMBED_MODEL` | `EMBED_MODEL` | `nomic-embed-text` | Model name |
| `EMBED_API_KEY` | `EMBED_API_KEY` | _(empty)_ | API key (required for cloud providers) |
| `EMBED_QUERY_PREFIX` | `EMBED_QUERY_PREFIX` | `search_query: ` | Prefix for search queries |
| `EMBED_DOCUMENT_PREFIX` | `EMBED_DOCUMENT_PREFIX` | `search_document: ` | Prefix for document chunks |

### Provider Examples

**Ollama** (default — local GPU):
```bash
EMBED_BASE_URL=http://localhost:11434/v1
EMBED_MODEL=nomic-embed-text
```

**llama-server / llama.cpp** (local CPU):
```bash
EMBED_BASE_URL=http://localhost:8080/v1
EMBED_MODEL=nomic-embed-text
```

**OpenAI**:
```bash
EMBED_BASE_URL=https://api.openai.com/v1
EMBED_MODEL=text-embedding-3-small
EMBED_API_KEY=sk-...
EMBED_QUERY_PREFIX=
EMBED_DOCUMENT_PREFIX=
```

**Azure OpenAI**:
```bash
EMBED_BASE_URL=https://your-resource.openai.azure.com/openai/deployments/your-deployment
EMBED_MODEL=text-embedding-3-small
EMBED_API_KEY=your-azure-key
EMBED_QUERY_PREFIX=
EMBED_DOCUMENT_PREFIX=
```

> **Note:** Asymmetric models like `nomic-embed-text` use different prefixes for queries vs documents.
> OpenAI and most cloud models are symmetric — set both prefixes to empty strings.

### Other Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `DEFAULT_COLLECTION` | `documents` | Default Qdrant collection |
| `DEFAULT_CHUNK_SIZE` | `512` | Words per chunk |
| `DEFAULT_CHUNK_OVERLAP` | `64` | Word overlap between chunks |
| `MCP_HTTP_PORT` | `8090` | HTTP transport port |
| `ALLOWED_INGEST_PATHS` | `/home/chohman/`, `/mnt/hdd/` | File ingestion whitelist |

## Dependencies

- `mcp[cli]>=1.18.0` — MCP SDK with FastMCP
- `qdrant-client>=1.17.0` — Qdrant Python client
- `pydantic>=2.0` — Input validation
- `pymupdf` — PDF text extraction (in Docker image)

Shared modules from `~/rag/lib/`: chunker, extractor, store. Embedding is handled by `qdrant_mcp/embeddings.py` (provider-agnostic).

## Logging

- **stdio mode**: Structured logs to stderr (keeps stdout clean for MCP protocol)
- **HTTP mode**: Structured logs to `~/logs/qdrant-mcp.log`
- Format: `2026-03-25 19:38:11  INFO   qdrant_mcp.search  ...`

## Error Handling

All tools return actionable error messages for common failures:

| Failure | Error message |
|---------|---------------|
| Ollama down | "Ollama is not reachable (embedding failed). Is it running on port 11434?" |
| Qdrant unreachable | "cannot reach Qdrant" / "cannot access collection" |
| Collection not found | "collection 'X' not found" |
| File not found | "file not found: /path" |
| Path outside whitelist | "path '/etc/passwd' is outside allowed directories" |
| Invalid parameters | Specific range/constraint messages |

## Health Monitoring

When `qdrant-mcp=on` in `~/logs/expected-state.conf`, the health monitor (`~/health.sh --cron`) will auto-restart the server if it goes down.
