import os
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct, Filter, FieldCondition, MatchValue
COLLECTION = "all_sites"
VECTOR_SIZE = 384

def get_client():
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_key = os.getenv("QDRANT_API_KEY")
    
    if qdrant_url and qdrant_key:
        # Cloud mode (Railway deployment)
        return QdrantClient(url=qdrant_url, api_key=qdrant_key)
    else:
        # Local mode (your PC)
        return QdrantClient(path="./qdrant_local")

def setup_collection(client: QdrantClient):
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION not in existing:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
        )

def store_chunks_for_site(chunks: list[dict], site_name: str):
    client = get_client()
    setup_collection(client)
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=c["vector"],
            payload={
                "text": c["text"],
                "source_url": c["source_url"],
                "site_name": site_name,
                "chunk_index": c["chunk_index"]
            }
        )
        for c in chunks
    ]
    client.upsert(collection_name=COLLECTION, points=points)
    return len(points)

# Keep old function name so app.py doesn't break
def store_chunks(chunks: list[dict]):
    return store_chunks_for_site(chunks, site_name="uploaded")

def clear_site(site_name: str):
    """Delete only chunks belonging to one site — leaves others untouched."""
    client = get_client()
    setup_collection(client)
    client.delete(
        collection_name=COLLECTION,
        points_selector=Filter(
            must=[FieldCondition(key="site_name", match=MatchValue(value=site_name))]
        )
    )

def clear_collection():
    client = get_client()
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION in existing:
        client.delete_collection(COLLECTION)
    setup_collection(client)

def list_sites():
    client = get_client()
    setup_collection(client)
    return COLLECTION

def search_chunks(query_vector: list[float], top_k: int = 8) -> list[dict]:
    client = get_client()
    results = client.query_points(
        collection_name=COLLECTION,
        query=query_vector,
        limit=top_k,
        with_payload=True
    ).points
    return [
        {
            "text": r.payload["text"],
            "source_url": r.payload["source_url"],
            "site_name": r.payload.get("site_name", "unknown"),
            "score": round(r.score, 3)
        }
        for r in results
    ]