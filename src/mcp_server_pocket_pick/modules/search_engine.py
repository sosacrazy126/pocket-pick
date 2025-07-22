"""
Unified Search Engine Module

This module provides a hybrid search system that combines vector similarity,
full-text search, and fuzzy matching to deliver optimal search results.
"""

import logging
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from .embeddings import EmbeddingGenerator, VectorSimilarity, serialize_embedding, deserialize_embedding
from .connection_pool import get_db_connection
from .data_types import PocketItem, FindCommand
from .init_db import normalize_tags
from thefuzz import fuzz

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Represents a search result with multiple scoring components"""
    item: PocketItem
    vector_score: float = 0.0
    fts_score: float = 0.0  
    fuzzy_score: float = 0.0
    total_score: float = 0.0
    match_reasons: List[str] = None
    
    def __post_init__(self):
        if self.match_reasons is None:
            self.match_reasons = []


@dataclass
class SearchConfig:
    """Configuration for search behavior"""
    # Scoring weights (should sum to 1.0)
    vector_weight: float = 0.4
    fts_weight: float = 0.35
    fuzzy_weight: float = 0.25
    
    # Thresholds
    vector_similarity_threshold: float = 0.3
    fuzzy_score_threshold: float = 50
    min_total_score: float = 0.1
    
    # Search limits
    max_results: int = 50
    vector_top_k: int = 100
    
    # Performance settings
    enable_caching: bool = True
    cache_ttl_minutes: int = 10
    parallel_search: bool = True
    embedding_batch_size: int = 32


class SearchCache:
    """Simple in-memory cache for search results"""
    
    def __init__(self, max_entries: int = 1000, ttl_minutes: int = 10):
        self.cache = {}
        self.access_times = {}
        self.max_entries = max_entries
        self.ttl = timedelta(minutes=ttl_minutes)
    
    def _cache_key(self, query: str, tags: List[str], mode: str) -> str:
        """Generate cache key from search parameters"""
        tag_str = ",".join(sorted(tags)) if tags else ""
        return f"{mode}:{query}:{tag_str}"
    
    def get(self, query: str, tags: List[str], mode: str) -> Optional[List[SearchResult]]:
        """Get cached search results if not expired"""
        key = self._cache_key(query, tags, mode)
        
        if key in self.cache:
            cached_time = self.access_times.get(key, datetime.min)
            if datetime.now() - cached_time < self.ttl:
                self.access_times[key] = datetime.now()
                return self.cache[key]
            else:
                # Remove expired entry
                self.cache.pop(key, None)
                self.access_times.pop(key, None)
        
        return None
    
    def set(self, query: str, tags: List[str], mode: str, results: List[SearchResult]):
        """Cache search results"""
        key = self._cache_key(query, tags, mode)
        
        # Remove oldest entries if cache is full
        if len(self.cache) >= self.max_entries:
            # Remove the oldest 10% of entries
            removal_count = max(1, self.max_entries // 10)
            oldest_keys = sorted(self.access_times.keys(), 
                               key=lambda k: self.access_times[k])[:removal_count]
            
            for old_key in oldest_keys:
                self.cache.pop(old_key, None)
                self.access_times.pop(old_key, None)
        
        self.cache[key] = results
        self.access_times[key] = datetime.now()
    
    def clear(self):
        """Clear all cached entries"""
        self.cache.clear()
        self.access_times.clear()


class HybridSearchEngine:
    """Unified search engine combining vector, FTS, and fuzzy search"""
    
    def __init__(self, config: Optional[SearchConfig] = None):
        self.config = config or SearchConfig()
        self.embedding_generator = None
        self.cache = SearchCache(ttl_minutes=self.config.cache_ttl_minutes)
        self._embedding_lock = asyncio.Lock()
        
    def _get_embedding_generator(self) -> EmbeddingGenerator:
        """Lazy initialization of embedding generator"""
        if self.embedding_generator is None:
            try:
                self.embedding_generator = EmbeddingGenerator(cache_enabled=True)
                logger.info("Embedding generator initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize embedding generator: {e}")
                raise
        return self.embedding_generator
    
    async def ensure_embeddings_exist(self, db_path: Path, batch_size: int = 32) -> bool:
        """Ensure all items in database have embeddings"""
        try:
            embedding_gen = self._get_embedding_generator()
            
            with get_db_connection(db_path) as conn:
                # Find items without embeddings
                cursor = conn.execute("""
                    SELECT id, text FROM POCKET_PICK 
                    WHERE embedding IS NULL OR embedding_updated IS NULL
                    ORDER BY created DESC
                """)
                items_to_embed = cursor.fetchall()
            
            if not items_to_embed:
                logger.debug("All items already have embeddings")
                return True
            
            logger.info(f"Generating embeddings for {len(items_to_embed)} items")
            
            # Process in batches
            for i in range(0, len(items_to_embed), batch_size):
                batch = items_to_embed[i:i + batch_size]
                batch_texts = [item[1] for item in batch]
                batch_ids = [item[0] for item in batch]
                
                # Generate embeddings for batch
                embeddings = embedding_gen.generate_embeddings_batch(batch_texts)
                
                # Store in database
                with get_db_connection(db_path) as conn:
                    for item_id, embedding in zip(batch_ids, embeddings):
                        serialized_embedding = serialize_embedding(embedding)
                        conn.execute("""
                            UPDATE POCKET_PICK 
                            SET embedding = ?, embedding_updated = ?
                            WHERE id = ?
                        """, (serialized_embedding, datetime.now().isoformat(), item_id))
                    conn.commit()
                
                logger.debug(f"Generated embeddings for batch {i//batch_size + 1}/{(len(items_to_embed) + batch_size - 1)//batch_size}")
            
            logger.info("Successfully generated all missing embeddings")
            return True
            
        except Exception as e:
            logger.error(f"Error ensuring embeddings exist: {e}")
            return False
    
    def _vector_search(self, query: str, db_path: Path, limit: int) -> List[Tuple[PocketItem, float]]:
        """Perform vector similarity search"""
        try:
            embedding_gen = self._get_embedding_generator()
            query_embedding = embedding_gen.generate_embedding(query)
            
            results = []
            
            with get_db_connection(db_path) as conn:
                cursor = conn.execute("""
                    SELECT id, created, text, tags, embedding 
                    FROM POCKET_PICK 
                    WHERE embedding IS NOT NULL
                """)
                
                embeddings = []
                items = []
                
                for row in cursor.fetchall():
                    item_id, created_str, text, tags_json, embedding_blob = row
                    
                    if embedding_blob:
                        # Deserialize embedding
                        embedding = deserialize_embedding(embedding_blob)
                        embeddings.append(embedding)
                        
                        # Parse item data
                        created = datetime.fromisoformat(created_str)
                        tags = json.loads(tags_json)
                        
                        item = PocketItem(
                            id=item_id,
                            created=created,
                            text=text,
                            tags=tags
                        )
                        items.append(item)
            
            if embeddings:
                # Find similar embeddings
                similarities = VectorSimilarity.similarity_search(
                    query_embedding, 
                    embeddings, 
                    top_k=limit,
                    similarity_threshold=self.config.vector_similarity_threshold
                )
                
                # Convert to results
                for idx, score in similarities:
                    if idx < len(items):
                        results.append((items[idx], score))
            
            return results
            
        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            return []
    
    def _fts_search(self, query: str, db_path: Path, tags: List[str], limit: int) -> List[Tuple[PocketItem, float]]:
        """Perform full-text search using SQLite FTS5"""
        try:
            results = []
            
            with get_db_connection(db_path) as conn:
                try:
                    # Try FTS5 search first
                    base_query = """
                        SELECT POCKET_PICK.id, POCKET_PICK.created, POCKET_PICK.text, POCKET_PICK.tags,
                               rank
                        FROM pocket_pick_fts 
                        JOIN POCKET_PICK ON pocket_pick_fts.rowid = POCKET_PICK.rowid
                        WHERE pocket_pick_fts MATCH ?
                    """
                    
                    params = [query]
                    where_clauses = []
                    
                    # Add tag filters
                    if tags:
                        normalized_tags = normalize_tags(tags)
                        tag_clauses = []
                        for tag in normalized_tags:
                            tag_clauses.append("POCKET_PICK.tags LIKE ?")
                            params.append(f"%\"{tag}\"%")
                        where_clauses.append(f"({' AND '.join(tag_clauses)})")
                    
                    if where_clauses:
                        base_query += f" AND {' AND '.join(where_clauses)}"
                    
                    base_query += f" ORDER BY rank LIMIT {limit}"
                    
                    cursor = conn.execute(base_query, params)
                    
                    for row in cursor.fetchall():
                        item_id, created_str, text, tags_json, rank = row
                        
                        created = datetime.fromisoformat(created_str)
                        item_tags = json.loads(tags_json)
                        
                        item = PocketItem(
                            id=item_id,
                            created=created,
                            text=text,
                            tags=item_tags
                        )
                        
                        # Convert rank to score (FTS5 rank is negative, lower is better)
                        # Normalize to 0-1 range
                        score = max(0.0, min(1.0, 1.0 + rank / 10.0))
                        results.append((item, score))
                    
                except Exception as fts_error:
                    logger.warning(f"FTS5 search failed: {fts_error}, falling back to LIKE search")
                    
                    # Fallback to LIKE-based search
                    search_words = query.split()
                    word_clauses = []
                    params = []
                    
                    for word in search_words:
                        word_clauses.append("text LIKE ?")
                        params.append(f"%{word}%")
                    
                    fallback_query = f"""
                        SELECT id, created, text, tags
                        FROM POCKET_PICK 
                        WHERE {' AND '.join(word_clauses)}
                    """
                    
                    # Add tag filters
                    if tags:
                        normalized_tags = normalize_tags(tags)
                        for tag in normalized_tags:
                            fallback_query += " AND tags LIKE ?"
                            params.append(f"%\"{tag}\"%")
                    
                    fallback_query += f" ORDER BY created DESC LIMIT {limit}"
                    
                    cursor = conn.execute(fallback_query, params)
                    
                    for row in cursor.fetchall():
                        item_id, created_str, text, tags_json = row
                        
                        created = datetime.fromisoformat(created_str)
                        item_tags = json.loads(tags_json)
                        
                        item = PocketItem(
                            id=item_id,
                            created=created,
                            text=text,
                            tags=item_tags
                        )
                        
                        # Simple scoring based on word matches
                        text_lower = text.lower()
                        query_lower = query.lower()
                        score = fuzz.partial_ratio(query_lower, text_lower) / 100.0
                        results.append((item, score))
            
            return results
            
        except Exception as e:
            logger.error(f"Error in FTS search: {e}")
            return []
    
    def _fuzzy_search(self, query: str, db_path: Path, tags: List[str], limit: int) -> List[Tuple[PocketItem, float]]:
        """Perform fuzzy string matching search"""
        try:
            results = []
            
            with get_db_connection(db_path) as conn:
                base_query = "SELECT id, created, text, tags FROM POCKET_PICK"
                params = []
                where_clauses = []
                
                # Add tag filters
                if tags:
                    normalized_tags = normalize_tags(tags)
                    tag_clauses = []
                    for tag in normalized_tags:
                        tag_clauses.append("tags LIKE ?")
                        params.append(f"%\"{tag}\"%")
                    where_clauses.append(f"({' AND '.join(tag_clauses)})")
                
                if where_clauses:
                    base_query += f" WHERE {' AND '.join(where_clauses)}"
                
                base_query += " ORDER BY created DESC"
                
                cursor = conn.execute(base_query, params)
                
                query_lower = query.lower()
                scored_items = []
                
                for row in cursor.fetchall():
                    item_id, created_str, text, tags_json = row
                    
                    # Calculate fuzzy scores
                    text_lower = text.lower()
                    partial_score = fuzz.partial_ratio(query_lower, text_lower)
                    token_score = fuzz.token_set_ratio(query_lower, text_lower)
                    
                    # Use the better of the two scores
                    best_score = max(partial_score, token_score)
                    
                    if best_score >= self.config.fuzzy_score_threshold:
                        created = datetime.fromisoformat(created_str)
                        item_tags = json.loads(tags_json)
                        
                        item = PocketItem(
                            id=item_id,
                            created=created,
                            text=text,
                            tags=item_tags
                        )
                        
                        # Normalize score to 0-1 range
                        normalized_score = best_score / 100.0
                        scored_items.append((item, normalized_score))
                
                # Sort by score and limit results
                scored_items.sort(key=lambda x: x[1], reverse=True)
                results = scored_items[:limit]
            
            return results
            
        except Exception as e:
            logger.error(f"Error in fuzzy search: {e}")
            return []
    
    async def search(self, command: FindCommand) -> List[SearchResult]:
        """Perform unified hybrid search"""
        # Check cache first
        if self.config.enable_caching:
            cached_results = self.cache.get(command.text, command.tags or [], command.mode)
            if cached_results:
                logger.debug("Returning cached search results")
                return cached_results[:command.limit]
        
        # Ensure embeddings exist for vector search
        await self.ensure_embeddings_exist(command.db_path)
        
        search_results = {}  # item_id -> SearchResult
        
        if self.config.parallel_search:
            # Run searches in parallel
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = {}
                
                # Submit search tasks
                if command.mode in ['hybrid', 'vector', 'fts']:
                    futures['vector'] = executor.submit(
                        self._vector_search, 
                        command.text, 
                        command.db_path, 
                        self.config.vector_top_k
                    )
                
                if command.mode in ['hybrid', 'fts']:
                    futures['fts'] = executor.submit(
                        self._fts_search, 
                        command.text, 
                        command.db_path, 
                        command.tags or [],
                        self.config.max_results
                    )
                
                if command.mode in ['hybrid', 'fuzzy']:
                    futures['fuzzy'] = executor.submit(
                        self._fuzzy_search, 
                        command.text, 
                        command.db_path, 
                        command.tags or [],
                        self.config.max_results
                    )
                
                # Collect results
                for search_type, future in futures.items():
                    try:
                        results = future.result(timeout=30)  # 30 second timeout
                        for item, score in results:
                            if item.id not in search_results:
                                search_results[item.id] = SearchResult(item=item)
                            
                            result = search_results[item.id]
                            if search_type == 'vector':
                                result.vector_score = score
                                result.match_reasons.append(f"Vector similarity: {score:.3f}")
                            elif search_type == 'fts':
                                result.fts_score = score
                                result.match_reasons.append(f"Text match: {score:.3f}")
                            elif search_type == 'fuzzy':
                                result.fuzzy_score = score
                                result.match_reasons.append(f"Fuzzy match: {score:.3f}")
                    
                    except Exception as e:
                        logger.error(f"Error in {search_type} search: {e}")
        
        else:
            # Run searches sequentially
            if command.mode in ['hybrid', 'vector']:
                vector_results = self._vector_search(command.text, command.db_path, self.config.vector_top_k)
                for item, score in vector_results:
                    if item.id not in search_results:
                        search_results[item.id] = SearchResult(item=item)
                    search_results[item.id].vector_score = score
                    search_results[item.id].match_reasons.append(f"Vector similarity: {score:.3f}")
            
            if command.mode in ['hybrid', 'fts']:
                fts_results = self._fts_search(command.text, command.db_path, command.tags or [], self.config.max_results)
                for item, score in fts_results:
                    if item.id not in search_results:
                        search_results[item.id] = SearchResult(item=item)
                    search_results[item.id].fts_score = score
                    search_results[item.id].match_reasons.append(f"Text match: {score:.3f}")
            
            if command.mode in ['hybrid', 'fuzzy']:
                fuzzy_results = self._fuzzy_search(command.text, command.db_path, command.tags or [], self.config.max_results)
                for item, score in fuzzy_results:
                    if item.id not in search_results:
                        search_results[item.id] = SearchResult(item=item)
                    search_results[item.id].fuzzy_score = score
                    search_results[item.id].match_reasons.append(f"Fuzzy match: {score:.3f}")
        
        # Calculate combined scores
        final_results = []
        for result in search_results.values():
            # Calculate weighted total score
            result.total_score = (
                result.vector_score * self.config.vector_weight +
                result.fts_score * self.config.fts_weight + 
                result.fuzzy_score * self.config.fuzzy_weight
            )
            
            # Only include results above minimum threshold
            if result.total_score >= self.config.min_total_score:
                final_results.append(result)
        
        # Sort by total score (highest first)
        final_results.sort(key=lambda x: x.total_score, reverse=True)
        
        # Limit results
        limited_results = final_results[:command.limit]
        
        # Cache results
        if self.config.enable_caching:
            self.cache.set(command.text, command.tags or [], command.mode, limited_results)
        
        logger.info(f"Hybrid search returned {len(limited_results)} results for query: '{command.text}'")
        return limited_results
    
    def clear_cache(self):
        """Clear search cache"""
        self.cache.clear()
        logger.info("Search cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'cached_entries': len(self.cache.cache),
            'max_entries': self.cache.max_entries,
            'ttl_minutes': self.cache.ttl.total_seconds() / 60
        }