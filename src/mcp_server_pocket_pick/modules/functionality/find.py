import sqlite3
import json
import asyncio
from datetime import datetime
from typing import List
import logging
import re
from ..data_types import FindCommand, PocketItem
from ..init_db import normalize_tags
from ..connection_pool import get_db_connection
from ..search_engine import HybridSearchEngine, SearchConfig

logger = logging.getLogger(__name__)

def find(command: FindCommand) -> List[PocketItem]:
    """
    Find items in the pocket pick database matching the search criteria
    
    Args:
        command: FindCommand with search parameters
        
    Returns:
        List[PocketItem]: List of matching items
    """
    
    # Use hybrid search for enhanced search modes
    if command.mode in ['hybrid', 'vector', 'semantic']:
        try:
            return _hybrid_find(command)
        except Exception as e:
            logger.warning(f"Hybrid search failed: {e}, falling back to traditional search")
    
    # Fall back to traditional search for other modes
    return _traditional_find(command)


def _hybrid_find(command: FindCommand) -> List[PocketItem]:
    """Use the new hybrid search engine"""
    try:
        # Create search engine with optimized config
        config = SearchConfig(
            vector_weight=0.4,
            fts_weight=0.35,
            fuzzy_weight=0.25,
            vector_similarity_threshold=0.3,
            fuzzy_score_threshold=50,
            min_total_score=0.1,
            max_results=command.limit * 2,  # Get more results for better ranking
            enable_caching=True,
            parallel_search=True
        )
        
        search_engine = HybridSearchEngine(config)
        
        # Run async search in sync context
        loop = None
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            # If we're already in an async context, create a new event loop
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, search_engine.search(command))
                search_results = future.result(timeout=60)
        else:
            search_results = loop.run_until_complete(search_engine.search(command))
        
        # Convert SearchResult objects back to PocketItem objects
        items = []
        for result in search_results[:command.limit]:
            items.append(result.item)
        
        logger.info(f"Hybrid search returned {len(items)} results for query: '{command.text}'")
        return items
        
    except Exception as e:
        logger.error(f"Error in hybrid search: {e}")
        raise


def _traditional_find(command: FindCommand) -> List[PocketItem]:
    """Traditional search using existing SQLite FTS and fuzzy matching"""
    # Normalize tags
    normalized_tags = normalize_tags(command.tags) if command.tags else []
    
    # Use connection pool for better performance  
    with get_db_connection(command.db_path) as conn:
        try:
            # Base query
            query = "SELECT id, created, text, tags FROM POCKET_PICK"
            params = []
            where_clauses = []
            
            # Apply search mode
            if command.text:
                if command.mode == "substr":
                    where_clauses.append("text LIKE ?")
                    params.append(f"%{command.text}%")
                elif command.mode == "fts":
                    try:
                        # First, try using FTS5 virtual table
                        query = """
                        SELECT POCKET_PICK.id, POCKET_PICK.created, POCKET_PICK.text, POCKET_PICK.tags 
                        FROM pocket_pick_fts 
                        JOIN POCKET_PICK ON pocket_pick_fts.rowid = POCKET_PICK.rowid
                        """
                        
                        # FTS5 query syntax
                        search_term = command.text
                        
                        # Set up FTS5 query parameters
                        where_clauses = ["pocket_pick_fts MATCH ?"]
                        params = [search_term]
                        
                        # Add tag filters if needed
                        if normalized_tags:
                            tag_clauses = []
                            for tag in normalized_tags:
                                tag_clauses.append("POCKET_PICK.tags LIKE ?")
                                params.append(f"%\"{tag}\"%")
                            where_clauses.append(f"({' AND '.join(tag_clauses)})")
                        
                        use_fts5 = True
                        
                    except sqlite3.OperationalError:
                        # Fallback to basic LIKE-based search if FTS5 is not available
                        logger.warning("FTS5 not available, falling back to basic search")
                        use_fts5 = False
                        
                        # Standard fallback approach
                        search_words = command.text.split()
                        word_clauses = []
                        for word in search_words:
                            word_clauses.append("text LIKE ?")
                            params.append(f"%{word}%")
                        where_clauses.append(f"({' AND '.join(word_clauses)})")
                        
                elif command.mode == "glob":
                    where_clauses.append("text GLOB ?")
                    params.append(command.text)
                elif command.mode == "regex":
                    # We'll need to filter with regex after query
                    pass
                elif command.mode == "exact":
                    where_clauses.append("text = ?")
                    params.append(command.text)
            
            # Apply tag filter if tags are specified
            if normalized_tags and command.mode != "fts":
                # Find items that have all the specified tags
                tag_clauses = []
                for tag in normalized_tags:
                    tag_clauses.append("tags LIKE ?")
                    params.append(f"%\"{tag}\"%")
                where_clauses.append(f"({' AND '.join(tag_clauses)})")
            
            # Handle query construction based on whether we're using FTS5
            if command.mode == "fts" and 'use_fts5' in locals() and use_fts5:
                # For FTS5, we've already constructed the base query
                if where_clauses:
                    query += f" WHERE {' AND '.join(where_clauses)}"
                query += f" ORDER BY rank, created DESC LIMIT {command.limit}"
                logger.debug(f"Using FTS5 query: {query}")
            else:
                # Standard query construction
                if where_clauses:
                    query += f" WHERE {' AND '.join(where_clauses)}"
                query += f" ORDER BY created DESC LIMIT {command.limit}"
            
            # Execute query
            try:
                cursor = conn.execute(query, params)
            except sqlite3.OperationalError as e:
                # If the FTS5 query fails, fall back to the basic query
                if command.mode == "fts" and 'use_fts5' in locals() and use_fts5:
                    logger.warning(f"FTS5 query failed: {e}. Falling back to basic search.")
                    
                    # Reset to base query
                    query = "SELECT id, created, text, tags FROM POCKET_PICK"
                    params = []
                    
                    # Standard fallback approach
                    if command.text:
                        search_words = command.text.split()
                        word_clauses = []
                        for word in search_words:
                            word_clauses.append("text LIKE ?")
                            params.append(f"%{word}%")
                        query += f" WHERE ({' AND '.join(word_clauses)})"
                        
                        # Re-add tag filters if needed
                        if normalized_tags:
                            tag_clauses = []
                            for tag in normalized_tags:
                                tag_clauses.append("tags LIKE ?")
                                params.append(f"%\"{tag}\"%")
                            query += f" AND ({' AND '.join(tag_clauses)})"
                    
                    query += f" ORDER BY created DESC LIMIT {command.limit}"
                    cursor = conn.execute(query, params)
                else:
                    # If it's not an FTS5 issue, re-raise the exception
                    raise
            
            # Process results
            results = []
            for row in cursor.fetchall():
                id, created_str, text, tags_json = row
                
                # Parse the created timestamp
                created = datetime.fromisoformat(created_str)
                
                # Parse the tags JSON
                tags = json.loads(tags_json)
                
                # Create item
                item = PocketItem(
                    id=id,
                    created=created,
                    text=text,
                    tags=tags
                )
                
                # Apply regex filter if needed (we do this after the SQL query)
                if command.mode == "regex" and command.text:
                    try:
                        pattern = re.compile(command.text, re.IGNORECASE)
                        if not pattern.search(text):
                            continue
                    except re.error:
                        logger.warning(f"Invalid regex pattern: {command.text}")
                        continue
                
                results.append(item)
            
            return results
        except Exception as e:
            logger.error(f"Error finding items: {e}")
            raise