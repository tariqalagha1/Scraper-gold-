"""FAISS index management."""
from typing import Any, Dict, List, Optional
import logging
import os
import pickle

import numpy as np

from app.config import settings


logger = logging.getLogger(__name__)


class FAISSIndexManager:
    """Manages FAISS indexes for vector storage and retrieval.
    
    Handles:
    - Index creation and loading
    - Adding embeddings to index
    - Persisting indexes to disk
    """
    
    def __init__(self, dimension: int = 384):
        """Initialize the FAISS index manager.
        
        Args:
            dimension: Dimension of embedding vectors
        """
        self.dimension = dimension
        self._indexes: Dict[int, Any] = {}  # user_id -> index
        self._metadata: Dict[int, List[Dict]] = {}  # user_id -> list of metadata
        self._index_dir = os.path.join(settings.STORAGE_ROOT, "faiss_indexes")
        os.makedirs(self._index_dir, exist_ok=True)
    
    async def add_items(
        self,
        items: List[Dict[str, Any]],
        user_id: int,
    ) -> int:
        """Add items with embeddings to the index.
        
        Args:
            items: List of items with embeddings
            user_id: User ID for scoped index
            
        Returns:
            Number of items added
        """
        try:
            import faiss
            
            # Get or create index for user
            index = self._get_or_create_index(user_id)
            
            # Extract embeddings
            embeddings = []
            metadata_list = []
            
            for item in items:
                embedding = item.get("embedding")
                if embedding:
                    embeddings.append(embedding)
                    metadata_list.append({
                        "item_id": item.get("item_id"),
                        "index_position": len(self._metadata.get(user_id, [])) + len(metadata_list),
                    })
            
            if not embeddings:
                return 0
            
            # Convert to numpy array
            embeddings_array = np.array(embeddings, dtype=np.float32)
            
            # Add to index
            index.add(embeddings_array)
            
            # Store metadata
            if user_id not in self._metadata:
                self._metadata[user_id] = []
            self._metadata[user_id].extend(metadata_list)
            
            # Save index
            await self._save_index(user_id)
            
            return len(embeddings)
            
        except Exception as e:
            logger.error(f"Error adding items to index: {str(e)}")
            raise
    
    async def search(
        self,
        query_embedding: List[float],
        user_id: int,
        k: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search the index for similar items.
        
        Args:
            query_embedding: Query embedding vector
            user_id: User ID for scoped index
            k: Number of results to return
            
        Returns:
            List of search results with scores
        """
        try:
            index = self._get_or_create_index(user_id)
            
            if index.ntotal == 0:
                return []
            
            # Convert query to numpy array
            query_array = np.array([query_embedding], dtype=np.float32)
            
            # Search
            distances, indices = index.search(query_array, min(k, index.ntotal))
            
            # Get metadata for results
            results = []
            metadata = self._metadata.get(user_id, [])
            
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                if idx >= 0 and idx < len(metadata):
                    results.append({
                        "index": int(idx),
                        "distance": float(distance),
                        "score": 1.0 / (1.0 + float(distance)),
                        "metadata": metadata[idx],
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching index: {str(e)}")
            return []
    
    def _get_or_create_index(self, user_id: int):
        """Get or create a FAISS index for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            FAISS index
        """
        import faiss
        
        if user_id not in self._indexes:
            # Try to load from disk
            index_path = os.path.join(self._index_dir, f"index_{user_id}.faiss")
            metadata_path = os.path.join(self._index_dir, f"metadata_{user_id}.pkl")
            
            if os.path.exists(index_path):
                self._indexes[user_id] = faiss.read_index(index_path)
                if os.path.exists(metadata_path):
                    with open(metadata_path, "rb") as f:
                        self._metadata[user_id] = pickle.load(f)
            else:
                # Create new index
                self._indexes[user_id] = faiss.IndexFlatL2(self.dimension)
                self._metadata[user_id] = []
        
        return self._indexes[user_id]
    
    async def _save_index(self, user_id: int) -> None:
        """Save index to disk.
        
        Args:
            user_id: User ID
        """
        import faiss
        
        if user_id in self._indexes:
            index_path = os.path.join(self._index_dir, f"index_{user_id}.faiss")
            metadata_path = os.path.join(self._index_dir, f"metadata_{user_id}.pkl")
            
            faiss.write_index(self._indexes[user_id], index_path)
            
            with open(metadata_path, "wb") as f:
                pickle.dump(self._metadata.get(user_id, []), f)
