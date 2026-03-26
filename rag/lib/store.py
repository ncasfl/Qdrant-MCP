"""
Qdrant vector store operations for RAG.

Handles collection creation, upserting chunks with metadata,
and semantic search.
"""

import hashlib
import uuid
from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointIdsList,
    PointStruct,
    VectorParams,
)


COLLECTION_NAME = "documents"
VECTOR_DIM = 768  # nomic-embed-text output dimension
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333


@dataclass
class SearchResult:
    text: str
    score: float
    source: str
    page: int | None
    chunk_index: int


def get_client(host: str = QDRANT_HOST, port: int = QDRANT_PORT) -> QdrantClient:
    return QdrantClient(host=host, port=port)


def ensure_collection(
    client: QdrantClient,
    collection: str = COLLECTION_NAME,
    vector_dim: int = VECTOR_DIM,
) -> None:
    """Create collection if it doesn't exist."""
    collections = [c.name for c in client.get_collections().collections]
    if collection not in collections:
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(
                size=vector_dim,
                distance=Distance.COSINE,
            ),
        )


def make_point_id(source: str, chunk_index: int) -> str:
    """Deterministic UUID from source path + chunk index. Enables re-ingestion."""
    key = f"{source}::chunk::{chunk_index}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))


def upsert_chunks(
    client: QdrantClient,
    chunks: list[dict],
    vectors: list[list[float]],
    source: str,
    collection: str = COLLECTION_NAME,
    batch_size: int = 100,
) -> int:
    """
    Upsert chunk embeddings into Qdrant.

    Args:
        client:     QdrantClient instance.
        chunks:     List of chunk dicts with keys: text, index, page, char_offset.
        vectors:    Corresponding embedding vectors.
        source:     Source file path.
        collection: Qdrant collection name.
        batch_size: Points per upsert call.

    Returns:
        Number of points upserted.
    """
    points = []
    for chunk, vector in zip(chunks, vectors):
        point_id = make_point_id(source, chunk["index"])
        points.append(PointStruct(
            id=point_id,
            vector=vector,
            payload={
                "text": chunk["text"],
                "source": source,
                "page": chunk["page"],
                "chunk_index": chunk["index"],
                "char_offset": chunk["char_offset"],
            },
        ))

    # Batch upsert
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        client.upsert(collection_name=collection, points=batch)

    return len(points)


def delete_source(
    client: QdrantClient,
    source: str,
    collection: str = COLLECTION_NAME,
) -> None:
    """Delete all chunks from a given source file."""
    client.delete(
        collection_name=collection,
        points_selector=Filter(
            must=[FieldCondition(key="source", match=MatchValue(value=source))]
        ),
    )


def delete_points(
    client: QdrantClient,
    point_ids: list[str],
    collection: str = COLLECTION_NAME,
) -> None:
    """Delete specific points by their IDs."""
    client.delete(
        collection_name=collection,
        points_selector=PointIdsList(points=point_ids),
    )


def search(
    client: QdrantClient,
    query_vector: list[float],
    limit: int = 5,
    source_filter: str | None = None,
    collection: str = COLLECTION_NAME,
) -> list[SearchResult]:
    """
    Semantic search against the vector store.

    Args:
        client:        QdrantClient instance.
        query_vector:  Embedded query vector.
        limit:         Max results to return.
        source_filter: Optional filter to specific source file.
        collection:    Qdrant collection name.

    Returns:
        List of SearchResult objects, ranked by relevance.
    """
    search_filter = None
    if source_filter:
        search_filter = Filter(
            must=[FieldCondition(key="source", match=MatchValue(value=source_filter))]
        )

    results = client.query_points(
        collection_name=collection,
        query=query_vector,
        query_filter=search_filter,
        limit=limit,
        with_payload=True,
    )

    return [
        SearchResult(
            text=hit.payload["text"],
            score=hit.score,
            source=hit.payload["source"],
            page=hit.payload.get("page"),
            chunk_index=hit.payload["chunk_index"],
        )
        for hit in results.points
    ]


def collection_stats(
    client: QdrantClient,
    collection: str = COLLECTION_NAME,
) -> dict:
    """Get collection info: point count, status."""
    try:
        info = client.get_collection(collection_name=collection)
        return {
            "collection": collection,
            "points": info.points_count,
            "status": str(info.status),
        }
    except Exception:
        return {"collection": collection, "points": 0, "status": "not_found"}
