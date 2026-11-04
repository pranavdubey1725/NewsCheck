import uuid

from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, VectorParams

from newscheck.embeddings import embed_passages, embed_query

VECTOR_SIZE = 384  # bge-small-en-v1.5
# Provisional, for bge-small-en-v1.5: pure noise scored ~0.37, on-topic passages ~0.70+.
# Its job is to drop noise, not to tell this event apart from related ones (ranking and the judge do that).
RELEVANCE_FLOOR = 0.5


class Passage(BaseModel):
    text: str
    url: str
    title: str
    source_id: int


class RetrievedPassage(BaseModel):
    passage: Passage
    score: float


class PassageIndex:
    """An in-memory vector index of passages for ONE check."""

    def __init__(self) -> None:
        self._client = QdrantClient(":memory:")
        self._collection = f"passages-{uuid.uuid4().hex[:12]}"
        self._client.create_collection(
            self._collection,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )

    def add(self, passages: list[Passage]) -> None:
        if not passages:
            return
        vectors = embed_passages([p.text for p in passages])
        points = [
            PointStruct(id=str(uuid.uuid4()), vector=v, payload=p.model_dump())
            for p, v in zip(passages, vectors)
        ]
        self._client.upsert(self._collection, points=points)

    def search(self, query: str, k: int = 4) -> list[RetrievedPassage]:
        hits = self._client.query_points(self._collection, query=embed_query(query), limit=k).points
        return [RetrievedPassage(passage=Passage(**h.payload), score=h.score) for h in hits]
    
    def search_source(self, query: str, source_id: int, k: int = 2) -> list[RetrievedPassage]:
        """Top-k passages for the query, from ONE source only."""
        hits = self._client.query_points(
            self._collection,
            query=embed_query(query),
            query_filter=Filter(must=[FieldCondition(key="source_id", match=MatchValue(value=source_id))]),
            limit=k,
        ).points
        return [RetrievedPassage(passage=Passage(**h.payload), score=h.score) for h in hits]