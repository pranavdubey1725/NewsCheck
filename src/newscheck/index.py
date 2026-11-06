import uuid

from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, VectorParams

from newscheck.embeddings import embed_passages, embed_query

import re

from rank_bm25 import BM25Okapi

RRF_K = 60  # standard RRF constant


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())

VECTOR_SIZE = 384  # bge-small-en-v1.5
# Provisional, for bge-small-en-v1.5: pure noise scored ~0.37, on-topic passages ~0.70+.
# Its job is to drop noise, not to tell this event apart from related ones (ranking and the judge do that).
RELEVANCE_FLOOR = 0.55


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
        self._passages: dict[int, list[Passage]] = {}

    def add(self, passages: list[Passage]) -> None:
        for p in passages:
            self._passages.setdefault(p.source_id, []).append(p)
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


    def search_source_hybrid(self, query: str, source_id: int, k: int = 2) -> list[RetrievedPassage]:
        """Top-k passages from ONE source, fusing dense and BM25 rankings with RRF."""
        passages = self._passages.get(source_id, [])
        if not passages:
            return []

        dense = self.search_source(query, source_id, k=len(passages))
        dense_rank = {r.passage.text: i for i, r in enumerate(dense)}
        dense_score = {r.passage.text: r.score for r in dense}

        bm25 = BM25Okapi([_tokens(p.text) for p in passages])
        bm25_scores = bm25.get_scores(_tokens(query))
        bm25_order = sorted(range(len(passages)), key=lambda i: bm25_scores[i], reverse=True)
        bm25_rank = {passages[i].text: rank for rank, i in enumerate(bm25_order)}

        def fused(p: Passage) -> float:
            return 1 / (RRF_K + dense_rank[p.text] + 1) + 1 / (RRF_K + bm25_rank[p.text] + 1)

        best = sorted(passages, key=fused, reverse=True)[:k]
        return [RetrievedPassage(passage=p, score=dense_score[p.text]) for p in best]