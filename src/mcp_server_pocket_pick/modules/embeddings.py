"""
Vector Embeddings Module

This module provides functionality for generating and managing text embeddings
for semantic search capabilities in the Pocket Pick knowledge base.
"""

import logging
import hashlib
import pickle
from typing import List, Tuple, Optional
from pathlib import Path
import numpy as np

logger = logging.getLogger(__name__)

class EmbeddingCache:
    """Simple disk-based cache for embeddings to avoid regenerating them repeatedly"""
    
    def __init__(self, cache_dir: Path = Path(".embeddings_cache")):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        
    def _get_cache_key(self, text: str, model_name: str) -> str:
        """Generate a cache key for the given text and model"""
        content = f"{model_name}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def get(self, text: str, model_name: str) -> Optional[np.ndarray]:
        """Retrieve cached embedding if it exists"""
        try:
            cache_key = self._get_cache_key(text, model_name)
            cache_file = self.cache_dir / f"{cache_key}.pkl"
            
            if cache_file.exists():
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
        except Exception as e:
            logger.warning(f"Error reading from embedding cache: {e}")
        return None
    
    def set(self, text: str, model_name: str, embedding: np.ndarray) -> None:
        """Store embedding in cache"""
        try:
            cache_key = self._get_cache_key(text, model_name)
            cache_file = self.cache_dir / f"{cache_key}.pkl"
            
            with open(cache_file, 'wb') as f:
                pickle.dump(embedding, f)
        except Exception as e:
            logger.warning(f"Error writing to embedding cache: {e}")


class EmbeddingGenerator:
    """Handles text embedding generation using sentence-transformers"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", cache_enabled: bool = True):
        """
        Initialize the embedding generator
        
        Args:
            model_name: Name of the sentence-transformer model to use
            cache_enabled: Whether to use disk caching for embeddings
        """
        self.model_name = model_name
        self.model = None
        self.cache = EmbeddingCache() if cache_enabled else None
        self._load_model()
    
    def _load_model(self):
        """Lazy load the sentence transformer model"""
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Successfully loaded embedding model: {self.model_name}")
        except ImportError as e:
            logger.error(f"sentence-transformers not available: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load embedding model {self.model_name}: {e}")
            raise
    
    def preprocess_text(self, text: str, max_length: int = 512) -> str:
        """
        Preprocess text for embedding generation
        
        Args:
            text: Input text to preprocess
            max_length: Maximum length in characters (will be chunked if longer)
            
        Returns:
            Preprocessed text
        """
        # Basic cleaning
        text = text.strip()
        
        # Remove excessive whitespace
        text = " ".join(text.split())
        
        # Truncate if too long (sentence-transformers has token limits)
        if len(text) > max_length:
            # Try to cut at sentence boundaries
            sentences = text[:max_length].split('.')
            if len(sentences) > 1:
                text = '.'.join(sentences[:-1]) + '.'
            else:
                text = text[:max_length]
        
        return text
    
    def chunk_text(self, text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
        """
        Split text into overlapping chunks for better embedding coverage
        
        Args:
            text: Input text to chunk
            chunk_size: Size of each chunk in characters
            overlap: Overlap between chunks in characters
            
        Returns:
            List of text chunks
        """
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to end at sentence boundary
            if end < len(text):
                # Look for sentence end within the last 100 characters
                last_period = text.rfind('.', end - 100, end)
                if last_period != -1 and last_period > start:
                    end = last_period + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start forward with overlap
            start = end - overlap
            
            # Avoid infinite loops
            if start >= len(text):
                break
        
        return chunks
    
    def generate_embedding(self, text: str, use_cache: bool = True) -> np.ndarray:
        """
        Generate embedding for a single text
        
        Args:
            text: Input text
            use_cache: Whether to use caching
            
        Returns:
            Embedding vector as numpy array
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            return np.zeros(384)  # all-MiniLM-L6-v2 produces 384-dim vectors
        
        # Check cache first
        if use_cache and self.cache:
            cached_embedding = self.cache.get(text, self.model_name)
            if cached_embedding is not None:
                return cached_embedding
        
        # Preprocess text
        processed_text = self.preprocess_text(text)
        
        # Generate embedding
        try:
            embedding = self.model.encode([processed_text])[0]
            embedding = embedding.astype(np.float32)  # Reduce memory usage
            
            # Cache the result
            if use_cache and self.cache:
                self.cache.set(text, self.model_name, embedding)
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Return zero vector as fallback
            return np.zeros(384)
    
    def generate_embeddings_batch(self, texts: List[str], use_cache: bool = True) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts efficiently
        
        Args:
            texts: List of input texts
            use_cache: Whether to use caching
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        embeddings = []
        texts_to_embed = []
        cache_indices = []
        
        # Check cache for each text
        for i, text in enumerate(texts):
            if use_cache and self.cache:
                cached_embedding = self.cache.get(text, self.model_name)
                if cached_embedding is not None:
                    embeddings.append(cached_embedding)
                    cache_indices.append(None)
                else:
                    embeddings.append(None)
                    texts_to_embed.append(self.preprocess_text(text))
                    cache_indices.append(len(texts_to_embed) - 1)
            else:
                embeddings.append(None)
                texts_to_embed.append(self.preprocess_text(text))
                cache_indices.append(len(texts_to_embed) - 1)
        
        # Generate embeddings for uncached texts
        if texts_to_embed:
            try:
                batch_embeddings = self.model.encode(texts_to_embed)
                batch_embeddings = [emb.astype(np.float32) for emb in batch_embeddings]
                
                # Fill in the results and cache them
                batch_idx = 0
                for i, cache_idx in enumerate(cache_indices):
                    if cache_idx is not None:
                        embedding = batch_embeddings[cache_idx]
                        embeddings[i] = embedding
                        
                        # Cache the result
                        if use_cache and self.cache:
                            self.cache.set(texts[i], self.model_name, embedding)
                        batch_idx += 1
                        
            except Exception as e:
                logger.error(f"Error generating batch embeddings: {e}")
                # Fill with zero vectors as fallback
                for i, emb in enumerate(embeddings):
                    if emb is None:
                        embeddings[i] = np.zeros(384)
        
        return embeddings
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model"""
        if self.model_name == "all-MiniLM-L6-v2":
            return 384
        else:
            # Generate a small test embedding to get the dimension
            test_embedding = self.generate_embedding("test")
            return len(test_embedding)


class VectorSimilarity:
    """Utilities for vector similarity calculations"""
    
    @staticmethod
    def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            # Normalize vectors
            v1_norm = v1 / np.linalg.norm(v1)
            v2_norm = v2 / np.linalg.norm(v2)
            
            # Calculate cosine similarity
            similarity = np.dot(v1_norm, v2_norm)
            
            # Handle numerical precision issues
            similarity = np.clip(similarity, -1.0, 1.0)
            
            return float(similarity)
            
        except Exception as e:
            logger.warning(f"Error calculating cosine similarity: {e}")
            return 0.0
    
    @staticmethod
    def euclidean_distance(v1: np.ndarray, v2: np.ndarray) -> float:
        """Calculate Euclidean distance between two vectors"""
        try:
            return float(np.linalg.norm(v1 - v2))
        except Exception as e:
            logger.warning(f"Error calculating Euclidean distance: {e}")
            return float('inf')
    
    @staticmethod
    def similarity_search(query_embedding: np.ndarray, 
                         embeddings: List[np.ndarray], 
                         top_k: int = 10,
                         similarity_threshold: float = 0.3) -> List[Tuple[int, float]]:
        """
        Find the most similar embeddings to a query embedding
        
        Args:
            query_embedding: Query vector
            embeddings: List of vectors to search through
            top_k: Number of top results to return
            similarity_threshold: Minimum similarity score to include
            
        Returns:
            List of (index, similarity_score) tuples, sorted by similarity
        """
        if not embeddings:
            return []
        
        similarities = []
        
        for i, embedding in enumerate(embeddings):
            if embedding is not None and embedding.size > 0:
                similarity = VectorSimilarity.cosine_similarity(query_embedding, embedding)
                if similarity >= similarity_threshold:
                    similarities.append((i, similarity))
        
        # Sort by similarity (highest first)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]


def serialize_embedding(embedding: np.ndarray) -> bytes:
    """Serialize embedding for database storage"""
    return embedding.tobytes()


def deserialize_embedding(data: bytes, dtype: np.dtype = np.float32, shape: Tuple[int, ...] = None) -> np.ndarray:
    """Deserialize embedding from database storage"""
    if shape is None:
        # Assume 384 dimensions for all-MiniLM-L6-v2
        shape = (384,)
    return np.frombuffer(data, dtype=dtype).reshape(shape)