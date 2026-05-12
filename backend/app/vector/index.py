"""PGVector index management."""
from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import uuid4

from app.config import settings


logger = logging.getLogger(__name__)


class _NoopEmbeddings:
    """Satisfies PGVector embedding interface when using precomputed vectors."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.0]


class PGVectorIndexManager:
    """Manages PGVector-backed vector storage and retrieval."""

    def __init__(self) -> None:
        self.collection_name = "scraper_vectors"
        self._store = None

    def _connection_string(self) -> str | None:
        connection = str(settings.DATABASE_URL or "").strip()
        if not connection.startswith("postgresql"):
            return None
        if connection.startswith("postgresql+asyncpg://"):
            return connection.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
        if connection.startswith("postgresql://"):
            return connection.replace("postgresql://", "postgresql+psycopg2://", 1)
        return connection

    def _get_store(self):
        if self._store is not None:
            return self._store

        from langchain_community.vectorstores import PGVector

        connection_string = self._connection_string()
        if not connection_string:
            raise RuntimeError("DATABASE_URL must be a PostgreSQL URL to use PGVector.")

        self._store = PGVector(
            connection_string=connection_string,
            embedding_function=_NoopEmbeddings(),
            collection_name=self.collection_name,
            use_jsonb=True,
        )
        return self._store

    async def add_items(self, items: list[dict[str, Any]], user_id: Any) -> int:
        """Add items with embeddings to the pgvector collection."""
        embeddings: list[list[float]] = []
        texts: list[str] = []
        metadatas: list[dict[str, Any]] = []
        ids: list[str] = []

        for item in items:
            embedding = item.get("embedding")
            if not embedding:
                continue
            item_id = item.get("item_id") or str(uuid4())
            embeddings.append(embedding)
            texts.append(
                str(item.get("text") or item.get("content") or item.get("title") or item_id)
            )
            metadatas.append(
                {
                    "item_id": str(item_id),
                    "user_id": str(user_id),
                }
            )
            ids.append(str(item_id))

        if not embeddings:
            return 0

        try:
            store = self._get_store()
            await asyncio.to_thread(
                store.add_embeddings,
                texts=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids,
            )
            return len(embeddings)
        except Exception as exc:
            logger.error("Error adding items to pgvector index: %s", exc)
            raise

    async def search(
        self,
        query_embedding: list[float],
        user_id: Any,
        k: int = 10,
    ) -> list[dict[str, Any]]:
        """Search the pgvector collection for similar items."""
        try:
            store = self._get_store()
            matches = await asyncio.to_thread(
                store.similarity_search_with_score_by_vector,
                embedding=query_embedding,
                k=k,
                filter={"user_id": str(user_id)},
            )
            results: list[dict[str, Any]] = []
            for index, (document, score) in enumerate(matches):
                metadata = document.metadata or {}
                raw_score = float(score)
                results.append(
                    {
                        "index": index,
                        "distance": raw_score,
                        "score": 1.0 / (1.0 + max(raw_score, 0.0)),
                        "metadata": metadata,
                    }
                )
            return results
        except Exception as exc:
            logger.error("Error searching pgvector index: %s", exc)
            return []
