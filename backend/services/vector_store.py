import time
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    PayloadSchemaType,
)
from langfuse import observe, get_client
from config import settings

# Cloud si QDRANT_URL está definido, local para desarrollo
_client = (
    QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None, timeout=60)
    if settings.qdrant_url
    else QdrantClient(path="./qdrant_data")
)


def ensure_collection() -> None:
    existing = [c.name for c in _client.get_collections().collections]
    if settings.qdrant_collection not in existing:
        _client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=settings.embedding_dim, distance=Distance.COSINE),
        )
        _client.create_payload_index(
            collection_name=settings.qdrant_collection,
            field_name="source",
            field_schema=PayloadSchemaType.KEYWORD,
        )


def drop_and_recreate_collection() -> None:
    existing = [c.name for c in _client.get_collections().collections]
    if settings.qdrant_collection in existing:
        _client.delete_collection(settings.qdrant_collection)
    ensure_collection()


def delete_by_source(source: str) -> None:
    ensure_collection()
    _client.delete(
        collection_name=settings.qdrant_collection,
        points_selector=Filter(
            must=[FieldCondition(key="source", match=MatchValue(value=source))]
        ),
    )


_UPSERT_BATCH = 16


def upsert_chunks(chunks: list[dict]) -> None:
    ensure_collection()
    points = [
        PointStruct(
            id=c["id"],
            vector=c["vector"],
            payload={k: v for k, v in c.items() if k not in ("id", "vector")},
        )
        for c in chunks
    ]
    for i in range(0, len(points), _UPSERT_BATCH):
        batch = points[i:i + _UPSERT_BATCH]
        for attempt in range(4):
            try:
                _client.upsert(collection_name=settings.qdrant_collection, points=batch)
                break
            except Exception as e:
                if attempt < 3:
                    time.sleep(3 * (attempt + 1))
                else:
                    raise


@observe(name="qdrant-search")
def search(
    vector: list[float],
    top_k: int = 5,
    filters: dict | None = None,
    source_types: list[str] | None = None,
) -> list[dict]:
    ensure_collection()
    must_conditions = (
        [FieldCondition(key=k, match=MatchValue(value=v)) for k, v in filters.items()]
        if filters
        else []
    )
    should_conditions = (
        [FieldCondition(key="source_type", match=MatchValue(value=st)) for st in source_types]
        if source_types
        else None
    )
    qdrant_filter = None
    if must_conditions or should_conditions:
        qdrant_filter = Filter(
            must=must_conditions or None,
            should=should_conditions,
        )

    response = _client.query_points(
        collection_name=settings.qdrant_collection,
        query=vector,
        limit=top_k,
        query_filter=qdrant_filter,
        with_payload=True,
    )

    results = [{"score": r.score, **r.payload} for r in response.points]

    get_client().update_current_span(
        metadata={
            "top_k": top_k,
            "num_results": len(results),
            "sources": [r.get("source", "unknown") for r in results],
            "scores": [round(r.get("score", 0), 4) for r in results],
        }
    )

    return results
