"""Embedding generation using supported providers."""
import logging
from typing import List, Optional

from app.config import settings


logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generates text embeddings using explicitly supported providers."""

    SUPPORTED_PROVIDERS = {"openai"}
    
    def __init__(self, provider: str = "openai", api_key: str | None = None):
        """Initialize the embedding generator.
        
        Args:
            provider: Embedding provider (openai or gemini)
        """
        provider = provider.lower().strip()
        if provider not in self.SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unsupported embedding provider: {provider}. "
                f"Supported providers: {', '.join(sorted(self.SUPPORTED_PROVIDERS))}"
            )
        self.provider = provider
        self.api_key = (api_key or "").strip()
        self._client = None
        self._client_api_key = ""

    def configure_api_key(self, api_key: str | None) -> None:
        self.api_key = str(api_key or "").strip()

    def _resolve_api_key(self) -> str:
        return self.api_key or settings.OPENAI_API_KEY.strip()

    def is_available(self) -> bool:
        if self.provider == "openai":
            return bool(self._resolve_api_key())
        return False
    
    async def generate(self, text: str) -> List[float]:
        """Generate embedding for text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        if not self.is_available():
            raise ValueError(f"{self.provider} embedding provider is not configured.")
        return await self._generate_openai(text)
    
    async def generate_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        for text in texts:
            embedding = await self.generate(text)
            embeddings.append(embedding)
        return embeddings
    
    async def _generate_openai(self, text: str) -> List[float]:
        """Generate embedding using OpenAI.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        try:
            # Lazy import to avoid loading if not needed
            from openai import AsyncOpenAI
            
            api_key = self._resolve_api_key()
            if self._client is None or self._client_api_key != api_key:
                self._client = AsyncOpenAI(api_key=api_key)
                self._client_api_key = api_key
            
            response = await self._client.embeddings.create(
                model=settings.OPENAI_EMBEDDING_MODEL,
                input=text,
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"OpenAI embedding error: {str(e)}")
            raise
