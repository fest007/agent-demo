"""Vector-store adapter used by RAG and semantic memory.

Development defaults to local Chroma. Production can switch to Qdrant by setting
VECTOR_STORE=qdrant and QDRANT_URL.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from agent.config import get_settings


@dataclass
class VectorQueryItem:
    id: str
    document: str
    metadata: dict
    distance: float | None = None
    score: float | None = None


class BaseVectorCollection:
    def count(self) -> int:
        raise NotImplementedError

    def add(
        self,
        *,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict],
        embeddings: list[list[float]],
    ) -> None:
        raise NotImplementedError

    def upsert(
        self,
        *,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict],
        embeddings: list[list[float]],
    ) -> None:
        raise NotImplementedError

    def get(self, where: dict | None = None, include: list[str] | None = None) -> dict:
        raise NotImplementedError

    def delete(self, ids: list[str] | None = None, where: dict | None = None) -> None:
        raise NotImplementedError

    def query(
        self,
        *,
        query_embedding: list[float],
        top_k: int,
        where: dict | None = None,
    ) -> list[VectorQueryItem]:
        raise NotImplementedError


class ChromaVectorCollection(BaseVectorCollection):
    def __init__(self, name: str):
        import chromadb

        settings = get_settings()
        client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        self._collection = client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    def count(self) -> int:
        return self._collection.count()

    def add(self, *, ids, documents, metadatas, embeddings) -> None:
        self._collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    def upsert(self, *, ids, documents, metadatas, embeddings) -> None:
        self._collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    def get(self, where: dict | None = None, include: list[str] | None = None) -> dict:
        kwargs: dict[str, Any] = {}
        if where:
            kwargs["where"] = where
        if include:
            kwargs["include"] = include
        return self._collection.get(**kwargs)

    def delete(self, ids: list[str] | None = None, where: dict | None = None) -> None:
        kwargs: dict[str, Any] = {}
        if ids is not None:
            kwargs["ids"] = ids
        if where is not None:
            kwargs["where"] = where
        self._collection.delete(**kwargs)

    def query(
        self,
        *,
        query_embedding: list[float],
        top_k: int,
        where: dict | None = None,
    ) -> list[VectorQueryItem]:
        if self.count() == 0:
            return []
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self.count()),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        ids = results.get("ids", [[]])[0]
        distances = results.get("distances", [[]])[0]
        return [
            VectorQueryItem(id=item_id, document=document, metadata=metadata, distance=distance)
            for item_id, document, metadata, distance in zip(ids, documents, metadatas, distances)
        ]


class QdrantVectorCollection(BaseVectorCollection):
    def __init__(self, name: str):
        from qdrant_client import QdrantClient
        from qdrant_client.http import models

        settings = get_settings()
        self._name = f"{settings.qdrant_collection_prefix}_{name}"
        self._models = models
        kwargs: dict[str, Any] = {"url": settings.qdrant_url}
        if settings.qdrant_api_key:
            kwargs["api_key"] = settings.qdrant_api_key
        self._client = QdrantClient(**kwargs)
        self._ensure_collection(settings.qdrant_vector_size)

    def _ensure_collection(self, vector_size: int) -> None:
        try:
            self._client.get_collection(self._name)
        except Exception:
            self._client.create_collection(
                collection_name=self._name,
                vectors_config=self._models.VectorParams(
                    size=vector_size,
                    distance=self._models.Distance.COSINE,
                ),
            )

    def _point_id(self, item_id: str) -> str:
        return str(uuid5(NAMESPACE_URL, f"{self._name}:{item_id}"))

    def _filter(self, where: dict | None):
        if not where:
            return None
        return self._models.Filter(
            must=[
                self._models.FieldCondition(
                    key=key,
                    match=self._models.MatchValue(value=value),
                )
                for key, value in where.items()
            ]
        )

    def _payload(self, document: str, metadata: dict, item_id: str) -> dict:
        return {
            "_id": item_id,
            "_document": document,
            **(metadata or {}),
        }

    def count(self) -> int:
        result = self._client.count(collection_name=self._name, exact=True)
        return int(result.count)

    def add(self, *, ids, documents, metadatas, embeddings) -> None:
        self.upsert(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)

    def upsert(self, *, ids, documents, metadatas, embeddings) -> None:
        points = [
            self._models.PointStruct(
                id=self._point_id(item_id),
                vector=embedding,
                payload=self._payload(document, metadata, item_id),
            )
            for item_id, document, metadata, embedding in zip(ids, documents, metadatas, embeddings)
        ]
        if points:
            self._client.upsert(collection_name=self._name, points=points)

    def get(self, where: dict | None = None, include: list[str] | None = None) -> dict:
        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict] = []
        next_page = None
        include = include or ["documents", "metadatas"]

        while True:
            points, next_page = self._client.scroll(
                collection_name=self._name,
                scroll_filter=self._filter(where),
                limit=256,
                offset=next_page,
                with_payload=True,
                with_vectors=False,
            )
            for point in points:
                payload = dict(point.payload or {})
                item_id = payload.pop("_id", str(point.id))
                document = payload.pop("_document", "")
                ids.append(item_id)
                if "documents" in include:
                    documents.append(document)
                if "metadatas" in include:
                    metadatas.append(payload)
            if next_page is None:
                break

        result: dict[str, Any] = {"ids": ids}
        if "documents" in include:
            result["documents"] = documents
        if "metadatas" in include:
            result["metadatas"] = metadatas
        return result

    def delete(self, ids: list[str] | None = None, where: dict | None = None) -> None:
        if ids is not None:
            self._client.delete(
                collection_name=self._name,
                points_selector=self._models.PointIdsList(
                    points=[self._point_id(item_id) for item_id in ids]
                ),
            )
            return
        if where is not None:
            self._client.delete(
                collection_name=self._name,
                points_selector=self._models.FilterSelector(filter=self._filter(where)),
            )

    def query(
        self,
        *,
        query_embedding: list[float],
        top_k: int,
        where: dict | None = None,
    ) -> list[VectorQueryItem]:
        if self.count() == 0:
            return []
        query_filter = self._filter(where)
        if hasattr(self._client, "query_points"):
            response = self._client.query_points(
                collection_name=self._name,
                query=query_embedding,
                query_filter=query_filter,
                limit=min(top_k, self.count()),
                with_payload=True,
            )
            points = response.points
        else:
            points = self._client.search(
                collection_name=self._name,
                query_vector=query_embedding,
                query_filter=query_filter,
                limit=min(top_k, self.count()),
                with_payload=True,
            )

        items: list[VectorQueryItem] = []
        for point in points:
            payload = dict(point.payload or {})
            item_id = payload.pop("_id", str(point.id))
            document = payload.pop("_document", "")
            score = getattr(point, "score", None)
            distance = 1 - score if score is not None else None
            items.append(
                VectorQueryItem(
                    id=item_id,
                    document=document,
                    metadata=payload,
                    distance=distance,
                    score=score,
                )
            )
        return items


@lru_cache(maxsize=8)
def get_vector_collection(name: str) -> BaseVectorCollection:
    settings = get_settings()
    backend = settings.vector_store.lower().strip()
    if backend == "qdrant":
        return QdrantVectorCollection(name)
    if backend == "chroma":
        return ChromaVectorCollection(name)
    raise ValueError(f"Unsupported VECTOR_STORE: {settings.vector_store}")
