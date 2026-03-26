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

## Usage Examples

Once the server is running and connected to your MCP client, interact through natural conversation:

### Searching documents

> **You:** Search my documents for contract termination clauses

```
Search results for: contract termination clauses

Collection: documents | Results: 3

[1] 0.8234 — services-agreement.pdf p.12 (chunk 23)
Either party may terminate this Agreement upon thirty (30) days written
notice to the other party. In the event of a material breach...

[2] 0.7891 — employee-handbook.pdf p.45 (chunk 67)
Employment may be terminated at will by either party with or without
cause, subject to the notice requirements in Section 8.2...
```

### Ingesting a file

> **You:** Ingest this PDF: /home/user/Documents/quarterly-report.pdf

```json
{
  "status": "ok",
  "file": "/home/user/Documents/quarterly-report.pdf",
  "collection": "documents",
  "pages_extracted": 24,
  "chunks_created": 47,
  "points_upserted": 47,
  "text_length": 38291
}
```

### Ingesting raw text

> **You:** Ingest this text as "meeting-notes-mar-25":
> We discussed the Q1 roadmap and agreed to prioritize the API redesign. Budget was approved for two additional headcount...

```json
{
  "status": "ok",
  "source": "meeting-notes-mar-25",
  "collection": "documents",
  "chunks_created": 1,
  "points_upserted": 1,
  "text_length": 142
}
```

### Browsing collections

> **You:** What collections do I have?

```
Qdrant Collections (2 total)

| Collection | Points | Dimension | Distance |
|------------|--------|-----------|----------|
| documents  | 198    | 768       | Cosine   |
| research   | 43     | 768       | Cosine   |
```

### Deleting documents

> **You:** Delete all chunks from source "old-report.pdf"

The server requires explicit confirmation for destructive operations — the LLM must pass `confirm=true`:

```json
{
  "status": "ok",
  "collection": "documents",
  "points_before": 198,
  "points_after": 185,
  "points_deleted": 13,
  "filter_source": "/home/user/Documents/old-report.pdf"
}
```

## Working with Documents

### Where to place files

Files must be in a directory listed in `ALLOWED_INGEST_PATHS` (configured in `config.py`). By default this is restrictive — **update it for your environment**:

```python
# config.py
ALLOWED_INGEST_PATHS = [
    "/home/youruser/Documents/",
    "/home/youruser/projects/",
    "/data/shared/",
]
```

Any path outside these directories will be rejected with an error. This is a security measure to prevent unintended file access.

### Supported file formats

| Format | Extensions | Notes |
|--------|-----------|-------|
| PDF | `.pdf` | Text extracted via pymupdf; page boundaries preserved in metadata |
| Plain text | `.txt` | Direct ingestion |
| Markdown | `.md` | Ingested as plain text (markup preserved in chunks) |
| CSV | `.csv` | Ingested as raw text — rows become part of chunks |
| JSON | `.json` | Ingested as raw text |
| HTML | `.html`, `.htm` | Raw HTML ingested (tags included); pre-process for cleaner results |
| Log files | `.log` | Direct ingestion |
| reStructuredText | `.rst` | Ingested as plain text |

Files with unrecognized extensions are attempted as plain text.

> **Not supported:** Word documents (`.docx`), Excel (`.xlsx`), images, audio, or scanned PDFs without OCR text layers. Convert these to PDF or text before ingesting.

### Tips for better retrieval

**Before ingesting:**

- **Clean your PDFs.** Scanned documents need an OCR text layer — check by trying to select text in a PDF viewer. If you can't select text, the PDF contains only images and will extract as empty.
- **Remove boilerplate.** Headers, footers, page numbers, and legal disclaimers in every page create noise. If you can pre-process them out, your search quality improves.
- **Split large documents by topic.** A 500-page manual ingested as one file works, but searching is more precise if you split it into logical sections (one file per chapter or topic).
- **Use descriptive source names.** The `source` parameter is searchable via `source_filter`. Names like `q1-2026-financial-review` are more useful than `doc1.pdf`.

**Tuning chunk settings:**

- **Default chunk size (512 words)** works well for most documents. Larger chunks (1000+) preserve more context but reduce precision. Smaller chunks (200) are more precise but may lose context.
- **Overlap (64 words)** ensures concepts that span chunk boundaries aren't lost. Increase to 100-128 for technical documents with long multi-sentence concepts.
- **Re-ingesting a source** with the same name overwrites previous chunks (deterministic IDs). You can safely re-ingest after updating a document.

**Organizing with collections:**

- Use the default `documents` collection for general use
- Create separate collections for different domains: `qdrant_ingest_file` accepts a `collection` parameter
- Example: `legal` for contracts, `technical` for specs, `research` for papers — then search within a specific collection for focused results

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

# Create and activate a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install pymupdf  # for PDF support
```

> **Why a virtual environment?** The server depends on `mcp`, `qdrant-client`, `pydantic`, and their transitive dependencies. A venv keeps these isolated from your system Python. The Claude Code MCP config and Docker image both handle this automatically — the venv is only needed for native/manual installs.

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
      "command": "/path/to/Qdrant-MCP/.venv/bin/python3",
      "args": ["-m", "qdrant_mcp", "--transport", "stdio"],
      "cwd": "/path/to/Qdrant-MCP",
      "env": {
        "PYTHONPATH": "/path/to/Qdrant-MCP"
      }
    }
  }
}
```

> **Note:** Point `command` to the venv Python binary so Claude Code uses the isolated environment. If you installed dependencies globally or use Docker, `python3` works instead.

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
