<p align="center">
  <h1 align="center">Qdrant MCP Server</h1>
  <p align="center">
    A self-contained RAG toolkit for AI assistants — vector database, document ingestion, and semantic search in one package
  </p>
</p>

<p align="center">
  <a href="#tools">Tools</a> &bull;
  <a href="#quickstart">Quickstart</a> &bull;
  <a href="#embedding-providers">Embedding Providers</a> &bull;
  <a href="#client-configuration">Client Configuration</a> &bull;
  <a href="#configuration-reference">Configuration</a> &bull;
  <a href="#docker">Docker</a> &bull;
  <a href="#troubleshooting">Troubleshooting</a>
</p>

---

Qdrant MCP Server gives AI assistants the ability to store, search, and manage documents using a built-in [Qdrant](https://qdrant.tech) vector database. It implements the [Model Context Protocol (MCP)](https://modelcontextprotocol.io), which means any MCP-compatible client — Claude Desktop, Claude Code, Claude.ai, or third-party tools — can use it as a knowledge base through natural conversation.

**How it works:** You ingest documents (PDFs, text files, or raw text). The server chunks them, generates embeddings via your choice of provider, and stores the vectors in Qdrant. When you ask a question, it embeds your query and returns the most relevant passages with source attribution and similarity scores.

**What's included:**

- **Qdrant vector database** — bundled in Docker, starts automatically with `docker compose up`. No separate installation needed. (Can also point at an existing Qdrant instance if you have one.)
- **6 MCP tools** — search, ingest text, ingest files (PDF/text/markdown/HTML), list collections, collection details, and delete — all accessible through conversation
- **Provider-agnostic embeddings** — works with any OpenAI-compatible API: local (Ollama, llama.cpp) or cloud (OpenAI, Anthropic/Voyage, Google, Azure). Switch providers by changing one URL.
- **Dual transport** — stdio for Claude Desktop and Claude Code, streamable HTTP for Claude.ai or any HTTP-capable MCP client
- **Cross-platform** — runs on Linux, macOS, and Windows via native Python or Docker

Built with [FastMCP](https://github.com/modelcontextprotocol/python-sdk) (Python).

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

Files must be in a directory listed in `ALLOWED_INGEST_PATHS` (configured in `config.py`). By default, this is set to your home directory — **narrow it for your environment**:

```python
# config.py — Linux / macOS
ALLOWED_INGEST_PATHS = [
    "/home/youruser/Documents/",
    "/home/youruser/projects/",
    "/data/shared/",
]

# config.py — Windows
ALLOWED_INGEST_PATHS = [
    "C:\\Users\\youruser\\Documents\\",
    "C:\\Users\\youruser\\projects\\",
    "D:\\shared\\",
]
```

Any path outside these directories will be rejected with an error. This is a security measure to prevent unintended file access. Paths are validated using `os.path.abspath()`, so both forward slashes and backslashes work on Windows.

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

| Tool | Description | readOnly | destructive | idempotent |
|------|-------------|:--------:|:-----------:|:----------:|
| `qdrant_search` | Semantic search with score threshold and source filtering | yes | no | yes |
| `qdrant_ingest_text` | Chunk, embed, and store raw text | no | no | no |
| `qdrant_ingest_file` | Extract text from PDF/text files, then ingest | no | no | no |
| `qdrant_list_collections` | List all collections with point counts and vector config | yes | no | yes |
| `qdrant_collection_info` | Detailed stats on a specific collection | yes | no | yes |
| `qdrant_delete` | Remove points by ID or source filter (requires `confirm=true`) | no | **yes** | yes |

All tools support both **markdown** and **json** response formats via the `response_format` parameter. Tool annotations follow the [MCP specification](https://modelcontextprotocol.io/specification/latest) and inform clients about tool behavior for permission and safety decisions.

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

### Required

- **Python 3.10+** (tested on 3.10 and 3.11) — *or* **Docker** (which bundles everything)
- **Qdrant** — bundled in `docker compose up`, or [install separately](https://qdrant.tech/documentation/guides/installation/) for native Python
- **An embedding provider** — any OpenAI-compatible `/v1/embeddings` endpoint (see [Embedding Providers](#embedding-providers))

### System Requirements

| Resource | Minimum | Recommended | Notes |
|----------|---------|-------------|-------|
| **RAM** | 512 MB | 1 GB+ | MCP server uses ~50 MB. Qdrant uses 100-500 MB depending on collection size. Local embedding models add 500 MB–4 GB. |
| **Disk** | 500 MB | 1 GB+ | Project + Python dependencies (~200 MB), Qdrant data (varies with ingested documents), pymupdf (~25 MB). |
| **GPU** | None | Optional | Only needed for local GPU-accelerated embeddings (Ollama). Cloud providers (OpenAI, Voyage) require no GPU. CPU embedding via llama.cpp works without a GPU. |
| **OS** | Linux, macOS, Windows | Linux | All platforms supported for native Python and Docker. |
| **Docker** | Not required | Optional | `docker compose up` starts both Qdrant and the MCP server. Native Python works without Docker (requires separate Qdrant install). |
| **Network** | localhost | LAN | Qdrant and embedding provider must be reachable. HTTP transport exposes port 8090 on the configured bind address. |

> **Scaling note:** RAM and disk grow with the amount of ingested data. Each 768-dimension vector (nomic-embed-text) uses ~3 KB in Qdrant. 10,000 document chunks ≈ 30 MB of vector data plus payload text storage. For most personal/team use, this is negligible.

## Quickstart

### 1. Clone and install

**Linux / macOS:**
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

> **Ubuntu/Debian note:** If `python3 -m venv` fails with "ensurepip is not available", install the venv package first: `sudo apt install python3.10-venv` (adjust version to match your Python).

**Windows (PowerShell):**
```powershell
git clone https://github.com/ncasfl/Qdrant-MCP.git
cd Qdrant-MCP

# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
pip install pymupdf
```

> **Windows note:** Use `python` (not `python3`) — Windows Python installers register as `python`. If you get a "not recognized" error, ensure Python is in your system PATH.

> **Why a virtual environment?** The server depends on `mcp`, `qdrant-client`, `pydantic`, and their transitive dependencies. A venv keeps these isolated from your system Python. The Claude Code MCP config and Docker image both handle this automatically — the venv is only needed for native/manual installs.

### 2. Configure your embedding provider

Edit `qdrant_mcp/config.py` or set environment variables:

**Linux / macOS (bash):**
```bash
export EMBED_BASE_URL=http://localhost:11434/v1
export EMBED_MODEL=nomic-embed-text

# For cloud providers:
export EMBED_BASE_URL=https://api.openai.com/v1
export EMBED_MODEL=text-embedding-3-small
export EMBED_API_KEY=sk-...
```

**Windows (PowerShell):**
```powershell
$env:EMBED_BASE_URL = "http://localhost:11434/v1"
$env:EMBED_MODEL = "nomic-embed-text"

# For cloud providers:
$env:EMBED_BASE_URL = "https://api.openai.com/v1"
$env:EMBED_MODEL = "text-embedding-3-small"
$env:EMBED_API_KEY = "sk-..."
```

### 3. Run the server

**Linux / macOS:**
```bash
# stdio (for Claude Code / Claude Desktop):
PYTHONPATH="$(pwd)" python3 -m qdrant_mcp --transport stdio

# HTTP (for Claude.ai or other HTTP clients):
PYTHONPATH="$(pwd)" python3 -m qdrant_mcp --transport streamable-http --port 8090
```

**Windows (PowerShell):**
```powershell
# stdio:
$env:PYTHONPATH = (Get-Location).Path
python -m qdrant_mcp --transport stdio

# HTTP:
$env:PYTHONPATH = (Get-Location).Path
python -m qdrant_mcp --transport streamable-http --port 8090
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

### Claude Desktop (stdio)

Add to your Claude Desktop config file:

| Platform | Config path |
|----------|-------------|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

**macOS / Linux:**
```json
{
  "mcpServers": {
    "qdrant": {
      "command": "/path/to/Qdrant-MCP/.venv/bin/python3",
      "args": ["-m", "qdrant_mcp", "--transport", "stdio"],
      "env": {
        "PYTHONPATH": "/path/to/Qdrant-MCP"
      }
    }
  }
}
```

**Windows:**
```json
{
  "mcpServers": {
    "qdrant": {
      "command": "C:\\path\\to\\Qdrant-MCP\\.venv\\Scripts\\python.exe",
      "args": ["-m", "qdrant_mcp", "--transport", "stdio"],
      "env": {
        "PYTHONPATH": "C:\\path\\to\\Qdrant-MCP",
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

> **Important:** Claude Desktop requires a **full restart** (quit and reopen, not just close the window) to pick up config changes. Use absolute paths — Claude Desktop does not inherit your shell's `PATH` or working directory. On Windows, add `PYTHONIOENCODING: utf-8` to avoid encoding issues.

<details>
<summary><strong>Debugging Claude Desktop connection</strong></summary>

Check the MCP logs if the server doesn't appear:

| Platform | Log path |
|----------|----------|
| macOS | `~/Library/Logs/Claude/mcp.log` and `mcp-server-qdrant.log` |
| Windows | `%APPDATA%\Claude\logs\` |

Common issues: JSON syntax errors in config (silent failure), wrong Python path, missing `PYTHONPATH`.
</details>

### Claude Code / VS Code Extension (stdio)

Add to your `~/.mcp.json` (or project-level `.mcp.json`):

**Linux / macOS:**
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

**Windows:**
```json
{
  "mcpServers": {
    "qdrant": {
      "command": "C:\\path\\to\\Qdrant-MCP\\.venv\\Scripts\\python.exe",
      "args": ["-m", "qdrant_mcp", "--transport", "stdio"],
      "cwd": "C:\\path\\to\\Qdrant-MCP",
      "env": {
        "PYTHONPATH": "C:\\path\\to\\Qdrant-MCP"
      }
    }
  }
}
```

> **Note:** Point `command` to the venv Python binary so Claude Code uses the isolated environment. If you installed dependencies globally or use Docker, `python3` (or `python` on Windows) works instead.

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
| `QDRANT_HOST` | `localhost` | Qdrant server host. Docker compose sets this to `qdrant` (container name) automatically. Override with `QDRANT_HOST` env var. |
| `QDRANT_PORT` | `6333` | Qdrant REST API port. Override with `QDRANT_PORT` env var. |

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

The `docker-compose.yaml` bundles **both Qdrant and the MCP server** — one command starts everything:

```bash
docker compose build
docker compose up -d
```

This starts:
- **Qdrant** (vector database) on port 6333 with persistent storage
- **qdrant-mcp** (MCP server) on port 8090, pre-configured to connect to the bundled Qdrant

Verify:
```bash
# Qdrant health
curl -s http://localhost:6333/healthz

# MCP server
curl -s http://localhost:8090/mcp
```

### Data persistence

Qdrant data is stored in a named Docker volume (`qdrant_data`). Your vectors and collections persist across:
- Container restarts (`docker compose restart`)
- Container rebuilds (`docker compose build && docker compose up -d`)
- `docker compose down` (stops containers, keeps volumes)

Data is only destroyed by explicitly removing the volume: `docker volume rm qdrant-mcp_qdrant_data`

### Embedding provider in Docker

The MCP server needs an embedding provider. By default, the compose file points at Ollama on your host machine via `host.docker.internal`:

```yaml
environment:
  - EMBED_BASE_URL=http://host.docker.internal:11434/v1
```

For **cloud providers** (no local Ollama needed), override in the compose file or a `.env` file:

```yaml
environment:
  - EMBED_BASE_URL=https://api.openai.com/v1
  - EMBED_MODEL=text-embedding-3-small
  - EMBED_API_KEY=${OPENAI_API_KEY}
```

> **Cloud providers work on all platforms** (Linux, macOS, Windows) with no additional configuration — embedding calls go out over the internet, not to localhost.

### Platform notes

<details>
<summary><strong>Linux</strong></summary>

Works out of the box. `host.docker.internal` resolves to the host via the `extra_hosts` directive in the compose file. Ollama and other host services are reachable.
</details>

<details>
<summary><strong>macOS / Windows (Docker Desktop)</strong></summary>

Works out of the box. Docker Desktop natively supports `host.docker.internal`. Ollama and other host services are reachable.

If you prefer not to use Docker, the native Python approach works well on macOS and Windows:
```bash
PYTHONPATH="$(pwd)" python3 -m qdrant_mcp --transport streamable-http --port 8090
```
Note: you'll still need Qdrant running separately (via Docker or [Qdrant Cloud](https://cloud.qdrant.io/)).
</details>

### Using an existing Qdrant instance

If you already have Qdrant running, you can skip the bundled one. Create a `docker-compose.override.yaml`:

```yaml
services:
  qdrant:
    # Replace bundled Qdrant with a no-op
    image: busybox
    command: ["true"]
    restart: "no"
    ports: !reset []
    volumes: !reset []
    deploy: !reset {}
  qdrant-mcp:
    environment:
      # Point at your existing Qdrant
      - QDRANT_HOST=your-qdrant-host
      - QDRANT_PORT=6333
```

> **Tip:** Add `docker-compose.override.yaml` to your `.gitignore` — it's deployment-specific.

For native Python installs, set `QDRANT_HOST` in your environment or edit `config.py` directly.

### Docker image details

| Component | Image | Size |
|-----------|-------|------|
| Qdrant | `qdrant/qdrant:v1.13.6` | ~100 MB |
| qdrant-mcp | Custom (`python:3.11-slim` + deps) | ~250 MB |

Both containers have resource limits (Qdrant: 1 GB RAM, MCP: 512 MB RAM).

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
├── rag/
│   └── lib/
│       ├── chunker.py       # Text chunking with overlap + page tracking
│       ├── extract.py       # PDF/text extraction via pymupdf
│       └── store.py         # Qdrant CRUD + search operations
├── Dockerfile
├── docker-compose.yaml
├── requirements.txt
├── LICENSE
└── README.md
```

### Bundled modules: `rag/lib/`

The server includes shared modules for text chunking (`chunker.py`), PDF extraction (`extract.py`), and Qdrant storage operations (`store.py`). These are bundled in the repository under `rag/lib/` and require no additional setup — they're included in `PYTHONPATH` automatically when you follow the quickstart instructions.

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

## Troubleshooting

<details>
<summary><strong>Server not found / ENOENT error</strong></summary>

**Symptom:** `spawn python3 ENOENT` or server doesn't appear in client.

**Cause:** The MCP client can't find the Python executable. Claude Desktop and some editors launch servers with a minimal `PATH` that doesn't include your shell's customizations (pyenv, nvm, conda, etc.).

**Fix:** Use the **absolute path** to the venv Python in your config:
```bash
# Find your venv Python path
which python3                              # system
/path/to/Qdrant-MCP/.venv/bin/python3     # venv (Linux/macOS)
/path/to/Qdrant-MCP/.venv/Scripts/python.exe  # venv (Windows)
```
</details>

<details>
<summary><strong>ModuleNotFoundError: No module named 'qdrant_mcp'</strong></summary>

**Cause:** `PYTHONPATH` is not set or points to the wrong directory.

**Fix:** Ensure your client config includes `PYTHONPATH` pointing to the project root:
```json
"env": {
  "PYTHONPATH": "/path/to/Qdrant-MCP"
}
```

If you also use `rag/lib/` modules, include the parent directory:
```json
"env": {
  "PYTHONPATH": "/path/to/Qdrant-MCP:/path/to/parent-containing-rag"
}
```
</details>

<details>
<summary><strong>ModuleNotFoundError: No module named 'mcp' (or qdrant_client, etc.)</strong></summary>

**Cause:** The `command` in your config points to system Python, but dependencies are installed in a virtual environment.

**Fix:** Point `command` to the venv Python binary, not `python3`:
```json
"command": "/path/to/Qdrant-MCP/.venv/bin/python3"
```
</details>

<details>
<summary><strong>Embedding failed / Ollama not reachable</strong></summary>

**Cause:** The embedding provider is not running or the URL is wrong.

**Fix:**
1. Verify your provider is running: `curl http://localhost:11434/v1/embeddings -d '{"model":"nomic-embed-text","input":["test"]}'`
2. Check `EMBED_BASE_URL` matches your provider's actual URL
3. For cloud providers, verify `EMBED_API_KEY` is set (check env var, not just config.py)
</details>

<details>
<summary><strong>Windows: npx not found for mcp-remote bridge</strong></summary>

**Cause:** Windows `spawn` doesn't invoke a shell by default, and `npx` is a shell script.

**Fix:** Use `cmd /c` as the command wrapper:
```json
{
  "command": "cmd",
  "args": ["/c", "npx", "mcp-remote", "http://127.0.0.1:8090/mcp"]
}
```
</details>

<details>
<summary><strong>Connection works from CLI but not from Claude Desktop</strong></summary>

**Cause:** Claude Desktop inherits a minimal environment. Variables like `PATH`, `HOME`, `PYTHONPATH`, and anything set in `.bashrc`/`.zshrc` are **not available**.

**Fix:** Set all required environment variables explicitly in the `env` block of your config. Use absolute paths everywhere — no `~`, `$HOME`, or relative paths.
</details>

<details>
<summary><strong>Silent config errors in Claude Desktop</strong></summary>

**Cause:** JSON syntax errors in `claude_desktop_config.json` fail silently — no error dialog.

**Fix:** Validate your JSON before saving:
```bash
python3 -m json.tool < ~/Library/Application\ Support/Claude/claude_desktop_config.json
```
</details>

## Debugging

### MCP Inspector

Test your server directly without a client using the [MCP Inspector](https://modelcontextprotocol.io/docs/tools/debugging):

```bash
# stdio mode
npx @modelcontextprotocol/inspector python3 -m qdrant_mcp --transport stdio

# HTTP mode (start server first, then point inspector at it)
npx @modelcontextprotocol/inspector --url http://localhost:8090/mcp
```

The Inspector provides an interactive UI to list tools, call them with parameters, and inspect responses.

### Server logs

| Mode | Location |
|------|----------|
| stdio | stderr (visible in terminal or client logs) |
| HTTP / Docker | `~/logs/qdrant-mcp.log` (configurable via `LOG_FILE` in config.py) |
| Claude Desktop | `~/Library/Logs/Claude/mcp-server-qdrant.log` (macOS) |

## Security Considerations

- **The server runs with user-level permissions.** Any file accessible to the user running the server can be read by `qdrant_ingest_file` (within `ALLOWED_INGEST_PATHS`). Configure the path whitelist carefully.
- **No authentication on HTTP transport.** The streamable HTTP endpoint on port 8090 has no auth. If you expose it beyond localhost, anyone who can reach the port can search, ingest, and delete data. Bind to `127.0.0.1` (change `MCP_HTTP_HOST` in config.py) if you don't need LAN access, or use a reverse proxy with auth.
- **API keys in environment variables.** `EMBED_API_KEY` is read from the environment or config.py. Avoid committing API keys to config.py — use environment variables or a `.env` file (already in `.gitignore`).
- **Qdrant access.** The server connects to Qdrant with no authentication by default. If your Qdrant instance contains sensitive data, enable [Qdrant API key authentication](https://qdrant.tech/documentation/guides/security/).

## Known Limitations

- **No streaming for large ingestions.** Ingesting a large PDF (hundreds of pages) blocks until complete. The server remains responsive for other tool calls (async), but the calling client will wait.
- **No OCR.** Scanned PDFs without a text layer extract as empty. Pre-process with an OCR tool (e.g., `ocrmypdf`) before ingesting.
- **No `.docx` / `.xlsx` support.** Convert to PDF or text first. Adding support via `python-docx` / `openpyxl` is straightforward if needed.
- **Chunk size is word-based, not token-based.** The chunker splits on whitespace, which approximates but doesn't exactly match model tokenization. This is sufficient for retrieval but not exact for token budgets.
- **Single embedding model per server instance.** All collections use the same embedding model/dimension. To use different models for different collections, run separate server instances with different configs.

## Contributing

This started as a personal infrastructure project and is shared as a reference implementation. Forks and adaptations are welcome. If you build something interesting on top of it, feel free to open an issue to share.

## License

[MIT](LICENSE)
