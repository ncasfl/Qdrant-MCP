<p align="center">
  <h1 align="center">Qdrant MCP Server</h1>
  <p align="center">
    Semantic search, document ingestion, and collection management over <a href="https://qdrant.tech">Qdrant</a> — powered by <a href="https://modelcontextprotocol.io">MCP</a>
  </p>
</p>

<p align="center">
  <a href="#tools">Tools</a> &bull;
  <a href="#quickstart">Quickstart</a> &bull;
  <a href="#embedding-providers">Embedding Providers</a> &bull;
  <a href="#client-configuration">Client Configuration</a> &bull;
  <a href="#configuration-reference">Configuration</a> &bull;
  <a href="#docker">Docker</a>
</p>

---

An [MCP](https://modelcontextprotocol.io) server that exposes your [Qdrant](https://qdrant.tech) vector database as tools for AI assistants. Ingest documents, search semantically, and manage collections — all through natural conversation.

Built with [FastMCP](https://github.com/modelcontextprotocol/python-sdk) (Python). Supports **any OpenAI-compatible embedding provider** — local (Ollama, llama.cpp) or cloud (OpenAI, Anthropic, Google, Azure).

## Why

- **Search your documents from any MCP client** — ask "find my notes about X" and get ranked results from Qdrant
- **Ingest files mid-conversation** — drop a PDF or text file and it's chunked, embedded, and searchable immediately
- **Provider-agnostic embeddings** — swap between local GPU, local CPU, or cloud APIs by changing one URL
- **Dual transport** — stdio for Claude Code, streamable HTTP for Claude.ai, OpenClaw, or any HTTP-capable client

## Tools

| Tool | Description | Type |
|------|-------------|------|
| `qdrant_search` | Semantic search with score threshold and source filtering | read-only |
| `qdrant_ingest_text` | Chunk, embed, and store raw text | write |
| `qdrant_ingest_file` | Extract text from PDF/text files, then ingest | write |
| `qdrant_list_collections` | List all collections with point counts and vector config | read-only |
| `qdrant_collection_info` | Detailed stats on a specific collection | read-only |
| `qdrant_delete` | Remove points by ID or source filter (requires `confirm=true`) | destructive |

All tools support both **markdown** and **json** response formats.

## Architecture

```
┌──────────────────────────────────────────────────┐
│                   MCP Clients                     │
│  Claude Code (stdio)  │  Claude.ai / OpenClaw     │
│                       │  (streamable HTTP :8090)  │
└──────────┬────────────┴──────────┬────────────────┘
           │                       │
           ▼                       ▼
┌──────────────────────────────────────────────────┐
│              qdrant_mcp (FastMCP)                  │
│                                                    │
│  embeddings.py ──→ Any OpenAI-compatible API       │
│  tools/        ──→ Qdrant client                   │
│  rag/lib/      ──→ Chunker, PDF extractor          │
└──────────┬───────────────────────┬────────────────┘
           │                       │
           ▼                       ▼
   Embedding Provider          Qdrant :6333
   (Ollama, OpenAI,           (vector store)
    llama.cpp, etc.)
```

## Prerequisites

- **Python 3.10+**
- **Qdrant** running and accessible (default: `localhost:6333`)
- **An embedding provider** — any OpenAI-compatible `/v1/embeddings` endpoint (see [Embedding Providers](#embedding-providers))

## Quickstart

### 1. Clone and install

```bash
git clone https://github.com/ncasfl/Qdrant-MCP.git
cd Qdrant-MCP
pip install -r requirements.txt
pip install pymupdf  # for PDF support
```

### 2. Configure your embedding provider

Edit `qdrant_mcp/config.py` or set environment variables:

```bash
# Example: Ollama running locally (default)
export EMBED_BASE_URL=http://localhost:11434/v1
export EMBED_MODEL=nomic-embed-text

# Example: OpenAI
export EMBED_BASE_URL=https://api.openai.com/v1
export EMBED_MODEL=text-embedding-3-small
export EMBED_API_KEY=sk-...
```

### 3. Run the server

**stdio** (for Claude Code):
```bash
PYTHONPATH="$(pwd)" python3 -m qdrant_mcp --transport stdio
```

**HTTP** (for Claude.ai, OpenClaw, or other HTTP clients):
```bash
PYTHONPATH="$(pwd)" python3 -m qdrant_mcp --transport streamable-http --port 8090
```

### 4. Connect a client

See [Client Configuration](#client-configuration) below.

## Embedding Providers

The server uses the OpenAI-compatible `/v1/embeddings` API format. This works with a wide range of providers out of the box.

### Local Providers

<details>
<summary><strong>Ollama</strong> (local GPU/CPU)</summary>

```bash
EMBED_BASE_URL=http://localhost:11434/v1
EMBED_MODEL=nomic-embed-text
# No API key needed
```

Install Ollama and pull a model:
```bash
ollama pull nomic-embed-text
```
</details>

<details>
<summary><strong>llama-server / llama.cpp</strong> (local CPU/GPU)</summary>

```bash
EMBED_BASE_URL=http://localhost:8080/v1
EMBED_MODEL=your-model-name
# No API key needed
```

Start llama-server with an embedding model:
```bash
llama-server -m your-embedding-model.gguf --embedding --port 8080
```
</details>

### Cloud Providers

<details>
<summary><strong>OpenAI</strong></summary>

```bash
EMBED_BASE_URL=https://api.openai.com/v1
EMBED_MODEL=text-embedding-3-small
EMBED_API_KEY=sk-...
EMBED_QUERY_PREFIX=
EMBED_DOCUMENT_PREFIX=
```

Models: `text-embedding-3-small` (1536-dim), `text-embedding-3-large` (3072-dim)
</details>

<details>
<summary><strong>Anthropic (Claude) via Voyage AI</strong></summary>

Anthropic recommends [Voyage AI](https://www.voyageai.com/) for embeddings:

```bash
EMBED_BASE_URL=https://api.voyageai.com/v1
EMBED_MODEL=voyage-3
EMBED_API_KEY=pa-...
EMBED_QUERY_PREFIX=
EMBED_DOCUMENT_PREFIX=
```

Models: `voyage-3` (1024-dim), `voyage-3-lite` (512-dim), `voyage-code-3` (code-optimized)
</details>

<details>
<summary><strong>Google Gemini</strong> (via OpenAI-compatible proxy)</summary>

Use [LiteLLM](https://github.com/BerriAI/litellm) as a proxy to expose Gemini's embedding API in OpenAI format:

```bash
# Start LiteLLM proxy
litellm --model gemini/text-embedding-004 --port 4000

# Configure qdrant_mcp
EMBED_BASE_URL=http://localhost:4000/v1
EMBED_MODEL=gemini/text-embedding-004
EMBED_API_KEY=your-gemini-key
EMBED_QUERY_PREFIX=
EMBED_DOCUMENT_PREFIX=
```
</details>

<details>
<summary><strong>Azure OpenAI</strong></summary>

```bash
EMBED_BASE_URL=https://your-resource.openai.azure.com/openai/deployments/your-deployment
EMBED_MODEL=text-embedding-3-small
EMBED_API_KEY=your-azure-key
EMBED_QUERY_PREFIX=
EMBED_DOCUMENT_PREFIX=
```
</details>

> **Asymmetric vs symmetric models:** Models like `nomic-embed-text` use different prefixes for queries (`search_query: `) and documents (`search_document: `) to improve retrieval quality. OpenAI, Voyage, and most cloud models are symmetric — set both prefixes to empty strings.

## Client Configuration

### Claude Code (stdio)

Add to your `~/.mcp.json` (or project-level `.mcp.json`):

```json
{
  "mcpServers": {
    "qdrant": {
      "command": "python3",
      "args": ["-m", "qdrant_mcp", "--transport", "stdio"],
      "cwd": "/path/to/Qdrant-MCP",
      "env": {
        "PYTHONPATH": "/path/to/Qdrant-MCP:/path/to/parent"
      }
    }
  }
}
```

Restart Claude Code to pick up the new server.

### Claude.ai (HTTP)

1. Start the server in HTTP mode (see [Quickstart](#quickstart) or [Docker](#docker))
2. In Claude.ai settings, add a remote MCP server: `http://your-host:8090/mcp`

### OpenClaw / Claude Code Forks (HTTP via mcp-remote)

For MCP clients that only support stdio, use [mcp-remote](https://www.npmjs.com/package/mcp-remote) as a bridge:

```json
{
  "mcpServers": {
    "qdrant": {
      "command": "npx",
      "args": ["mcp-remote", "http://127.0.0.1:8090/mcp"]
    }
  }
}
```

### Any OpenAI-compatible Client

The HTTP endpoint at `/mcp` speaks the standard MCP streamable HTTP protocol. Any MCP-compatible client can connect.

## Configuration Reference

All settings can be configured in `qdrant_mcp/config.py` or overridden with environment variables.

### Embedding

| Env Var | Default | Description |
|---------|---------|-------------|
| `EMBED_BASE_URL` | `http://localhost:11434/v1` | OpenAI-compatible embeddings API base URL |
| `EMBED_MODEL` | `nomic-embed-text` | Embedding model name |
| `EMBED_API_KEY` | _(empty)_ | API key for cloud providers |
| `EMBED_QUERY_PREFIX` | `search_query: ` | Prefix prepended to search queries |
| `EMBED_DOCUMENT_PREFIX` | `search_document: ` | Prefix prepended to document chunks |

### Qdrant

| Setting | Default | Description |
|---------|---------|-------------|
| `QDRANT_HOST` | `localhost` | Qdrant server host |
| `QDRANT_PORT` | `6333` | Qdrant REST API port |

### Server

| Setting | Default | Description |
|---------|---------|-------------|
| `MCP_HTTP_PORT` | `8090` | HTTP transport port |
| `MCP_HTTP_HOST` | `0.0.0.0` | HTTP bind address |
| `DEFAULT_COLLECTION` | `documents` | Default Qdrant collection |
| `DEFAULT_CHUNK_SIZE` | `512` | Words per chunk |
| `DEFAULT_CHUNK_OVERLAP` | `64` | Word overlap between chunks |

### Security

| Setting | Default | Description |
|---------|---------|-------------|
| `ALLOWED_INGEST_PATHS` | _(configure per deployment)_ | Whitelist of directories for `qdrant_ingest_file` |

> **Important:** Update `ALLOWED_INGEST_PATHS` in `config.py` to match your environment. The default restricts file ingestion to specific directories.

## Docker

### Build and run

```bash
# Build (uses project root as build context)
docker compose build

# Start
docker compose up -d

# Verify
curl -s http://localhost:8090/mcp
```

The Docker image:
- Based on `python:3.11-slim`
- Includes all Python dependencies + pymupdf
- Uses host networking (needs access to Qdrant and embedding provider on localhost)
- Resource limits: 512MB RAM, 2 CPUs

### Environment variables in Docker

Pass embedding config via `docker-compose.yaml`:

```yaml
services:
  qdrant-mcp:
    # ... existing config ...
    environment:
      - EMBED_BASE_URL=https://api.openai.com/v1
      - EMBED_MODEL=text-embedding-3-small
      - EMBED_API_KEY=${OPENAI_API_KEY}
```

## Project Structure

```
Qdrant-MCP/
├── qdrant_mcp/
│   ├── __init__.py
│   ├── __main__.py          # Entry point: --transport stdio|streamable-http
│   ├── server.py            # FastMCP server, lifespan, logging setup
│   ├── config.py            # All configuration constants
│   ├── embeddings.py        # Provider-agnostic OpenAI-compatible embedding client
│   └── tools/
│       ├── search.py        # qdrant_search
│       ├── ingest.py        # qdrant_ingest_text, qdrant_ingest_file
│       ├── collections.py   # qdrant_list_collections, qdrant_collection_info
│       └── delete.py        # qdrant_delete
├── Dockerfile
├── docker-compose.yaml
├── requirements.txt
├── LICENSE
└── README.md
```

### External dependency: `rag/lib/`

The server imports shared modules for text chunking (`chunker.py`), PDF extraction (`extract.py`), and Qdrant storage operations (`store.py`). These must be available on `PYTHONPATH`. See the [rag/lib/](https://github.com/ncasfl/Qdrant-MCP) directory structure or adapt to your own chunking/extraction pipeline.

## Logging

| Mode | Destination | Notes |
|------|-------------|-------|
| stdio | stderr | Keeps stdout clean for MCP protocol |
| HTTP | Log file (configurable) | Default: `~/logs/qdrant-mcp.log` |

Log format: `2026-03-25 19:38:11  INFO   qdrant_mcp.search  Embedding query: ...`

Each tool module has its own logger (`qdrant_mcp.search`, `qdrant_mcp.ingest`, `qdrant_mcp.delete`, `qdrant_mcp.collections`).

## Error Handling

All tools return actionable error messages rather than raw tracebacks:

| Failure | Message |
|---------|---------|
| Embedding provider unreachable | "Ollama is not reachable (embedding failed). Is it running on port 11434?" |
| Qdrant unreachable | "cannot reach Qdrant" |
| Collection not found | "collection 'X' not found" |
| File not found | "file not found: /path/to/file" |
| Path outside whitelist | "path is outside allowed directories" |
| Invalid parameters | Specific range/constraint messages |
| PDF extraction failed | "failed to extract text from /path — {details}" |

## Contributing

This started as a personal infrastructure project and is shared as a reference implementation. Forks and adaptations are welcome. If you build something interesting on top of it, feel free to open an issue to share.

## License

[MIT](LICENSE)
