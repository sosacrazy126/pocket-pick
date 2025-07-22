"""
Caching Layer Module

This module provides intelligent caching for embeddings, search results,
and frequently accessed data to improve performance.
"""

import logging
import json
import hashlib
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, TypeVar, Generic
from dataclasses import dataclass
import numpy as np

try:
    import diskcache
    DISKCACHE_AVAILABLE = True
except ImportError:
    DISKCACHE_AVAILABLE = False
    logging.warning("diskcache not available, using memory-only caching")

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class CacheEntry:
    """Represents a cached item with metadata"""
    data: Any
    created_at: datetime
    accessed_at: datetime
    access_count: int = 0
    expires_at: Optional[datetime] = None
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def touch(self):
        """Update access time and count"""
        self.accessed_at = datetime.now()
        self.access_count += 1


class LRUCache(Generic[T]):
    """Least Recently Used cache with optional TTL"""
    
    def __init__(self, max_size: int = 1000, ttl_minutes: Optional[int] = None):
        self.max_size = max_size
        self.ttl = timedelta(minutes=ttl_minutes) if ttl_minutes else None
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []
        self._lock = threading.RLock()
    
    def _evict_expired(self):
        """Remove expired entries"""
        if self.ttl is None:
            return
        
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            self._remove_key(key)
    
    def _remove_key(self, key: str):
        """Remove a key from cache and access order"""
        self._cache.pop(key, None)
        if key in self._access_order:
            self._access_order.remove(key)
    
    def _evict_lru(self):
        """Remove least recently used entries if cache is full"""
        while len(self._cache) >= self.max_size and self._access_order:
            lru_key = self._access_order[0]
            self._remove_key(lru_key)
    
    def _update_access_order(self, key: str):
        """Update access order for LRU tracking"""
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
    
    def get(self, key: str) -> Optional[T]:
        """Get item from cache"""
        with self._lock:
            self._evict_expired()
            
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            if entry.is_expired():
                self._remove_key(key)
                return None
            
            entry.touch()
            self._update_access_order(key)
            return entry.data
    
    def set(self, key: str, value: T, ttl_minutes: Optional[int] = None):
        """Set item in cache"""
        with self._lock:
            self._evict_expired()
            self._evict_lru()
            
            expires_at = None
            if ttl_minutes is not None:
                expires_at = datetime.now() + timedelta(minutes=ttl_minutes)
            elif self.ttl is not None:
                expires_at = datetime.now() + self.ttl
            
            entry = CacheEntry(
                data=value,
                created_at=datetime.now(),
                accessed_at=datetime.now(),
                expires_at=expires_at
            )
            
            self._cache[key] = entry
            self._update_access_order(key)
    
    def delete(self, key: str) -> bool:
        """Delete item from cache"""
        with self._lock:
            if key in self._cache:
                self._remove_key(key)
                return True
            return False
    
    def clear(self):
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
    
    def size(self) -> int:
        """Get current cache size"""
        with self._lock:
            return len(self._cache)
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_accesses = sum(entry.access_count for entry in self._cache.values())
            avg_accesses = total_accesses / len(self._cache) if self._cache else 0
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'total_accesses': total_accesses,
                'average_accesses_per_item': avg_accesses,
                'ttl_minutes': self.ttl.total_seconds() / 60 if self.ttl else None
            }


class DiskCache:
    """Persistent disk-based cache using diskcache"""
    
    def __init__(self, cache_dir: Path, size_limit: int = 1024**3):  # 1GB default
        self.cache_dir = cache_dir
        self.size_limit = size_limit
        
        if not DISKCACHE_AVAILABLE:
            raise ImportError("diskcache package required for disk caching")
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache = diskcache.Cache(str(self.cache_dir), size_limit=size_limit)
    
    def get(self, key: str) -> Any:
        """Get item from disk cache"""
        try:
            return self._cache.get(key)
        except Exception as e:
            logger.warning(f"Error reading from disk cache: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """Set item in disk cache"""
        try:
            expire_time = ttl_seconds if ttl_seconds else None
            self._cache.set(key, value, expire=expire_time)
        except Exception as e:
            logger.warning(f"Error writing to disk cache: {e}")
    
    def delete(self, key: str) -> bool:
        """Delete item from disk cache"""
        try:
            return self._cache.delete(key)
        except Exception as e:
            logger.warning(f"Error deleting from disk cache: {e}")
            return False
    
    def clear(self):
        """Clear disk cache"""
        try:
            self._cache.clear()
        except Exception as e:
            logger.warning(f"Error clearing disk cache: {e}")
    
    def stats(self) -> Dict[str, Any]:
        """Get disk cache statistics"""
        try:
            return {
                'size': len(self._cache),
                'volume': self._cache.volume(),
                'size_limit': self.size_limit,
            }
        except Exception as e:
            logger.warning(f"Error getting disk cache stats: {e}")
            return {'error': str(e)}


class EmbeddingCache:
    """Specialized cache for text embeddings"""
    
    def __init__(self, 
                 memory_cache_size: int = 512,
                 disk_cache_dir: Optional[Path] = None,
                 disk_cache_size_limit: int = 512 * 1024 * 1024):  # 512MB
        
        self.memory_cache = LRUCache[np.ndarray](
            max_size=memory_cache_size, 
            ttl_minutes=60  # 1 hour TTL for embeddings
        )
        
        self.disk_cache = None
        if disk_cache_dir and DISKCACHE_AVAILABLE:
            try:
                self.disk_cache = DiskCache(disk_cache_dir, disk_cache_size_limit)
                logger.info(f"Disk cache enabled for embeddings: {disk_cache_dir}")
            except Exception as e:
                logger.warning(f"Failed to initialize disk cache: {e}")
    
    def _hash_key(self, text: str, model_name: str) -> str:
        """Generate hash key for text and model combination"""
        content = f"{model_name}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def get_embedding(self, text: str, model_name: str) -> Optional[np.ndarray]:
        """Get cached embedding"""
        key = self._hash_key(text, model_name)
        
        # Try memory cache first
        embedding = self.memory_cache.get(key)
        if embedding is not None:
            return embedding
        
        # Try disk cache
        if self.disk_cache:
            cached_data = self.disk_cache.get(key)
            if cached_data is not None:
                try:
                    # Deserialize numpy array
                    embedding = np.frombuffer(cached_data['embedding'], dtype=np.float32)
                    embedding = embedding.reshape(cached_data['shape'])
                    
                    # Store in memory cache for faster access
                    self.memory_cache.set(key, embedding)
                    return embedding
                except Exception as e:
                    logger.warning(f"Error deserializing cached embedding: {e}")
        
        return None
    
    def set_embedding(self, text: str, model_name: str, embedding: np.ndarray):
        """Cache embedding"""
        key = self._hash_key(text, model_name)
        
        # Store in memory cache
        self.memory_cache.set(key, embedding)
        
        # Store in disk cache
        if self.disk_cache:
            try:
                cached_data = {
                    'embedding': embedding.tobytes(),
                    'shape': embedding.shape,
                    'dtype': str(embedding.dtype)
                }
                self.disk_cache.set(key, cached_data, ttl_seconds=7 * 24 * 3600)  # 1 week
            except Exception as e:
                logger.warning(f"Error caching embedding to disk: {e}")
    
    def clear(self):
        """Clear all cached embeddings"""
        self.memory_cache.clear()
        if self.disk_cache:
            self.disk_cache.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = {
            'memory_cache': self.memory_cache.stats()
        }
        
        if self.disk_cache:
            stats['disk_cache'] = self.disk_cache.stats()
        
        return stats


class SearchResultCache:
    """Cache for search results with query-based keys"""
    
    def __init__(self, max_size: int = 1000, ttl_minutes: int = 10):
        self.cache = LRUCache[List[Dict[str, Any]]](
            max_size=max_size,
            ttl_minutes=ttl_minutes
        )
    
    def _cache_key(self, query: str, tags: List[str], mode: str, **kwargs) -> str:
        """Generate cache key for search parameters"""
        # Sort tags for consistent key generation
        sorted_tags = sorted(tags) if tags else []
        
        # Include additional parameters
        key_data = {
            'query': query.lower().strip(),
            'tags': sorted_tags,
            'mode': mode,
            **kwargs
        }
        
        # Create hash of the key data
        key_json = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_json.encode()).hexdigest()
    
    def get_results(self, query: str, tags: List[str], mode: str, **kwargs) -> Optional[List[Dict[str, Any]]]:
        """Get cached search results"""
        key = self._cache_key(query, tags, mode, **kwargs)
        return self.cache.get(key)
    
    def set_results(self, query: str, tags: List[str], mode: str, results: List[Dict[str, Any]], **kwargs):
        """Cache search results"""
        key = self._cache_key(query, tags, mode, **kwargs)
        self.cache.set(key, results)
    
    def clear(self):
        """Clear all cached search results"""
        self.cache.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.cache.stats()


class PatternIndexCache:
    """Cache for pattern index data"""
    
    def __init__(self, ttl_minutes: int = 30):
        self.cache = LRUCache[Dict[str, Any]](
            max_size=10,  # Small cache for index data
            ttl_minutes=ttl_minutes
        )
    
    def get_index(self, patterns_path: str) -> Optional[Dict[str, Any]]:
        """Get cached pattern index"""
        return self.cache.get(patterns_path)
    
    def set_index(self, patterns_path: str, index_data: Dict[str, Any]):
        """Cache pattern index"""
        self.cache.set(patterns_path, index_data)
    
    def invalidate_index(self, patterns_path: str):
        """Remove specific pattern index from cache"""
        self.cache.delete(patterns_path)
    
    def clear(self):
        """Clear all cached indices"""
        self.cache.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.cache.stats()


class CacheManager:
    """Centralized cache management"""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or Path(".cache")
        self.cache_dir.mkdir(exist_ok=True)
        
        # Initialize specialized caches
        self.embeddings = EmbeddingCache(
            disk_cache_dir=self.cache_dir / "embeddings"
        )
        self.search_results = SearchResultCache()
        self.pattern_index = PatternIndexCache()
        
        logger.info(f"Cache manager initialized with cache directory: {self.cache_dir}")
    
    def clear_all(self):
        """Clear all caches"""
        self.embeddings.clear()
        self.search_results.clear()
        self.pattern_index.clear()
        logger.info("All caches cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        return {
            'embeddings': self.embeddings.stats(),
            'search_results': self.search_results.stats(),
            'pattern_index': self.pattern_index.stats(),
            'cache_directory': str(self.cache_dir)
        }
    
    def warm_up(self, db_path: Path):
        """Pre-warm caches with frequently accessed data"""
        # This could be implemented to pre-load popular embeddings
        # or search results based on usage patterns
        logger.info("Cache warm-up completed")


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None
_cache_lock = threading.Lock()


def get_cache_manager(cache_dir: Optional[Path] = None) -> CacheManager:
    """Get or create global cache manager"""
    global _cache_manager
    
    with _cache_lock:
        if _cache_manager is None:
            _cache_manager = CacheManager(cache_dir)
        
        return _cache_manager


def clear_all_caches():
    """Clear all global caches"""
    
    with _cache_lock:
        if _cache_manager:
            _cache_manager.clear_all()