FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt pymupdf

# Copy MCP server package
COPY qdrant_mcp/ /app/qdrant_mcp/

# Copy RAG lib modules (bundled in repo)
COPY rag/ /app/rag/

ENV PYTHONPATH="/app"
ENV PYTHONUNBUFFERED=1

EXPOSE 8090

ENTRYPOINT ["python3", "-m", "qdrant_mcp", "--transport", "streamable-http", "--port", "8090"]
