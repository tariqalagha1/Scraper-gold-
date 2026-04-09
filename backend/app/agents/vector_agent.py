"""Vector Agent - FAISS embeddings and semantic search.

Single Responsibility: Generate embeddings and manage vector search.
This agent is responsible for:
- Generating text embeddings using GPT/Gemini
- Storing embeddings in FAISS index
- Performing semantic search queries
"""
from typing import Any, Dict, List, Optional

from app.agents.base_agent import BaseAgent
from app.vector.embeddings import EmbeddingGenerator
from app.vector.search import SemanticSearch
from app.vector.store import get_vector_store, vector_store_enabled


class VectorAgent(BaseAgent):
    """Handles FAISS embeddings and semantic search.
    
    Single Responsibility: Vector embeddings and similarity search.
    
    This agent manages the vector database operations including
    embedding generation and semantic search capabilities.
    """
    
    def __init__(self):
        """Initialize the Vector Agent."""
        super().__init__(agent_name="vector_agent")
        self.embedding_generator = EmbeddingGenerator()
        self.index_manager = None
        self.semantic_search = SemanticSearch()

    def _skip_response(self, reason: str) -> dict:
        return self.success_response(
            data={
                "status": "skipped",
                "optional": True,
                "reason": reason,
                "embeddings_generated": 0,
                "embeddings": [],
            }
        )

    def _configure_embedding_provider(self, providers: dict[str, Any] | None) -> None:
        provider_values = providers if isinstance(providers, dict) else {}
        self.embedding_generator.configure_api_key(provider_values.get(self.embedding_generator.provider))
    
    async def execute(self, input_data: dict) -> dict:
        """Process data for vector operations.
        
        Args:
            input_data: Data and operation specification:
                - operation: "embed", "search", or "index"
                - items: Data items to process (for embed/index)
                - query: Search query (for search)
                - user_id: User ID for scoped operations
                
        Returns:
            Structured response with operation results
        """
        # Validate required fields
        validation_error = self.validate_input(input_data, ["operation"])
        if validation_error:
            return self.fail_response(error=validation_error)
        
        operation = input_data["operation"]
        self._configure_embedding_provider(input_data.get("providers"))
        if not vector_store_enabled():
            return self._skip_response("vector_store_disabled")
        if not self.embedding_generator.is_available():
            return self._skip_response("embedding_provider_unconfigured")

        if operation == "embed":
            return await self._embed_items(input_data)
        elif operation == "search":
            return await self._search(input_data)
        elif operation == "index":
            return await self._index_items(input_data)
        else:
            return self.fail_response(error=f"Unknown operation: {operation}")
    
    async def _embed_items(self, input_data: dict) -> dict:
        """Generate embeddings for items.
        
        Args:
            input_data: Contains items to embed
            
        Returns:
            Response with embedding results
        """
        items = input_data.get("items", [])
        if not items:
            return self.fail_response(error="No items provided for embedding")
        
        embeddings = []
        for item in items:
            try:
                text = self._extract_text(item)
                if text:
                    embedding = await self.retry_operation(
                        self.embedding_generator.generate,
                        text,
                        max_retries=3
                    )
                    embeddings.append({
                        "item_id": item.get("id") or item.get("source_url") or item.get("title") or f"item-{len(embeddings)}",
                        "embedding": embedding,
                        "text_length": len(text),
                    })
            except Exception as e:
                self.logger.warning(f"Failed to embed item: {str(e)}")
                continue
        
        return self.success_response(data={
            "status": "success",
            "optional": True,
            "provider": self.embedding_generator.provider,
            "embeddings_generated": len(embeddings),
            "embeddings": embeddings,
        })
    
    async def _search(self, input_data: dict) -> dict:
        """Perform semantic search.
        
        Args:
            input_data: Contains search query and parameters
            
        Returns:
            Response with search results
        """
        query = input_data.get("query")
        if not query:
            return self.fail_response(error="No query provided for search")
        
        user_id = input_data.get("user_id")
        limit = input_data.get("limit", 10)
        
        try:
            # Generate query embedding
            query_embedding = await self.embedding_generator.generate(query)
            
            # Search the index
            results = await self.semantic_search.search(
                query_embedding=query_embedding,
                user_id=user_id,
                limit=limit,
            )
            
            return self.success_response(data={
                "query": query,
                "results_count": len(results),
                "results": results,
            })
            
        except Exception as e:
            return self.fail_response(error=f"Search failed: {str(e)}")
    
    async def _index_items(self, input_data: dict) -> dict:
        """Add items to the FAISS index.
        
        Args:
            input_data: Contains items with embeddings to index
            
        Returns:
            Response with indexing results
        """
        items = input_data.get("items", [])
        user_id = input_data.get("user_id")
        
        if not items:
            return self.fail_response(error="No items provided for indexing")
        
        try:
            index_manager = get_vector_store()
            if index_manager is None:
                return self.success_response(data={
                    "status": "skipped",
                    "optional": True,
                    "items_indexed": 0,
                })

            indexed_count = await index_manager.add_items(
                items=items,
                user_id=user_id,
            )
            
            return self.success_response(data={
                "status": "success",
                "optional": True,
                "items_indexed": indexed_count,
            })
            
        except Exception as e:
            return self.success_response(data={
                "status": "failed",
                "optional": True,
                "items_indexed": 0,
                "error": f"Indexing failed: {str(e)}",
            })
    
    def _extract_text(self, item: dict) -> Optional[str]:
        """Extract searchable text from an item.
        
        Args:
            item: Data item
            
        Returns:
            Extracted text or None
        """
        # Try common text fields
        for field in ["content", "text", "title", "description"]:
            if field in item and item[field]:
                value = item[field]
                if isinstance(value, str):
                    return value
                elif isinstance(value, dict):
                    return str(value)
        
        return None
