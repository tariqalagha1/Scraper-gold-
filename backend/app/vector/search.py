"""Semantic search queries using FAISS."""
from typing import Any, Dict, List, Optional
import logging

from app.vector.embeddings import EmbeddingGenerator
from app.vector.index import FAISSIndexManager


logger = logging.getLogger(__name__)


class SemanticSearch:
    """Performs semantic search using FAISS.
    
    Combines embedding generation with FAISS search.
    """
    
    def __init__(self):
        """Initialize the semantic search."""
        self.embedding_generator = EmbeddingGenerator()
        self.index_manager = FAISSIndexManager()
    
    async def search(
        self,
        query_embedding: List[float],
        user_id: int,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
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
    ) -> List[Dict[str, Any]]:
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
) -> List[int]:
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
