from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.config import settings

_client = AsyncQdrantClient(
    url=settings.qdrant_url,
    api_key=settings.qdrant_api_key,
)


async def search(query_vector: list[float], limit: int = 5) -> list[str]:
    """Search the Qdrant collection and return payload text snippets."""
    results = await _client.query_points(
        collection_name=settings.qdrant_collection,
        query=query_vector,
        limit=limit,
        with_payload=True,
    )
    return [hit.payload.get("text", "") for hit in results.points if hit.payload]


async def upsert(points: list[PointStruct]) -> None:
    """Upsert points into the Qdrant collection."""
    await _client.upsert(
        collection_name=settings.qdrant_collection,
        points=points,
    )


async def ensure_collection(vector_size: int = 768) -> None:
    """Create the collection if it doesn't exist."""
    collections = await _client.get_collections()
    names = [c.name for c in collections.collections]
    if settings.qdrant_collection not in names:
        await _client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
