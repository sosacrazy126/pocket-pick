"""
Pattern Search Module

This module implements the search functionality for patterns, leveraging
the slug-based index to provide fast and intuitive pattern lookup.
"""

import logging
from typing import List, Optional, Tuple
from pathlib import Path

from ..data_types import PatternSearchCommand, PatternItem, GetPatternCommand
from .index_patterns import (
    get_index, find_in_index, slug_to_content, resolve_slug, get_similar_slugs
)

logger = logging.getLogger(__name__)

def search_patterns(command: PatternSearchCommand) -> List[PatternItem]:
    """
    Search for patterns matching the query.
    
    Args:
        command: PatternSearchCommand with query, patterns_path, limit, fuzzy
        
    Returns:
        List[PatternItem]: List of matching patterns
    """
    logger.info(f"Searching for patterns matching '{command.query}'")
    
    # Get pattern index
    index = get_index(str(command.patterns_path))
    
    # Search in index
    results = find_in_index(command.query, index, command.fuzzy)
    
    # Limit results
    results = results[:command.limit]
    
    # Convert to PatternItem objects
    pattern_items = []
    for score, metadata in results:
        # Load pattern content
        content = slug_to_content(metadata.slug, str(command.patterns_path))
        if content:
            pattern_item = PatternItem(
                slug=metadata.slug,
                title=metadata.title,
                summary=metadata.summary,
                tags=metadata.tags,
                content=content,
                score=score
            )
            pattern_items.append(pattern_item)
    
    logger.info(f"Found {len(pattern_items)} matching patterns")
    return pattern_items

def get_pattern(command: GetPatternCommand) -> Optional[PatternItem]:
    """
    Get a pattern by slug or query.
    
    Args:
        command: GetPatternCommand with slug, patterns_path, fuzzy
        
    Returns:
        Optional[PatternItem]: The pattern if found, None otherwise
    """
    logger.info(f"Getting pattern for slug '{command.slug}'")
    
    # Try to resolve slug
    result = resolve_slug(command.slug, str(command.patterns_path))
    
    if result:
        slug, content = result
        
        # Get metadata from index
        index = get_index(str(command.patterns_path))
        metadata = index.get(slug)
        
        if metadata:
            return PatternItem(
                slug=slug,
                title=metadata.title,
                summary=metadata.summary,
                tags=metadata.tags,
                content=content,
                score=1.0
            )
    
    # If not found and in fuzzy mode, suggest similar patterns
    if command.fuzzy:
        similar_slugs = get_similar_slugs(command.slug, str(command.patterns_path))
        if similar_slugs:
            similar_str = ", ".join(similar_slugs)
            logger.info(f"Pattern '{command.slug}' not found. Similar slugs: {similar_str}")
            # Return None but log the similar slugs
            return None
    
    logger.warning(f"Pattern '{command.slug}' not found")
    return None