"""Semantic search queries using PGVector."""
from typing import Any
import logging

from app.vector.embeddings import EmbeddingGenerator
from app.vector.index import PGVectorIndexManager


logger = logging.getLogger(__name__)


class SemanticSearch:
    """Performs semantic search using PGVector."""
    
    def __init__(self):
        """Initialize the semantic search."""
        self.embedding_generator = EmbeddingGenerator()
        self.index_manager = PGVectorIndexManager()
    
    async def search(
        self,
        query_embedding: list[float],
        user_id: Any,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search for similar items using embedding.
        
        Args:
            query_embedding: Query embedding vector
            user_id: User ID for scoped search
            limit: Maximum number of results
            
        Returns:
            List of search results
        """
        return await self.index_manager.search(
            query_embedding=query_embedding,
            user_id=user_id,
            k=limit,
        )
    
    async def search_by_text(
        self,
        query: str,
        user_id: int,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search for similar items using text query.
        
        Args:
            query: Text query
            user_id: User ID for scoped search
            limit: Maximum number of results
            
        Returns:
            List of search results
        """
        # Generate embedding for query
        query_embedding = await self.embedding_generator.generate(query)
        
        # Search
        return await self.search(
            query_embedding=query_embedding,
            user_id=user_id,
            limit=limit,
        )


# Convenience function for result_service
async def semantic_search(
    query: str,
    user_id: int,
    limit: int = 10,
) -> list[int]:
    """Perform semantic search and return result IDs.
    
    Args:
        query: Text query
        user_id: User ID for scoped search
        limit: Maximum number of results
        
    Returns:
        List of result IDs
    """
    search = SemanticSearch()
    results = await search.search_by_text(query, user_id, limit)
    
    return [
        r["metadata"]["item_id"]
        for r in results
        if r.get("metadata", {}).get("item_id")
    ]
