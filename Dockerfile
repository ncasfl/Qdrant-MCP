FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY qdrant-mcp/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt pymupdf

# Copy MCP server package
COPY qdrant-mcp/qdrant_mcp/ /app/qdrant_mcp/

# Copy shared RAG lib modules
COPY rag/lib/ /app/rag/lib/
RUN touch /app/rag/__init__.py

ENV PYTHONPATH="/app"
ENV PYTHONUNBUFFERED=1

EXPOSE 8090

ENTRYPOINT ["python3", "-m", "qdrant_mcp", "--transport", "streamable-http", "--port", "8090"]
