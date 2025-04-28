"""
Pattern Indexing Module

This module is responsible for discovering, indexing, and providing fast access to
patterns stored in the patterns directory. It uses folder slugs as primary identifiers
and provides functions to build and query a pattern index.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field
from thefuzz import fuzz

logger = logging.getLogger(__name__)

class PatternMetadata(BaseModel):
    """Metadata for a pattern including its location and key attributes"""
    slug: str
    title: str
    summary: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    full_path: Path
    system_md_path: Optional[Path] = None
    user_md_path: Optional[Path] = None

def extract_metadata_from_markdown(file_path: Path) -> Dict[str, Any]:
    """
    Extract title and summary from a markdown file.
    Tags are now handled externally by index_patterns based on pattern_descriptions.json.

    Args:
        file_path: Path to the markdown file

    Returns:
        Dict containing metadata (title, summary)
    """
    metadata = {
        "title": None,
        "summary": None,
        # Tags are no longer extracted here
    }

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read(2000)  # Read first 2000 chars for metadata extraction

            # Extract title from heading
            lines = content.split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith("# "):
                    metadata["title"] = line[2:].strip()
                    break

            # If no title found, use filename
            if not metadata["title"]:
                metadata["title"] = file_path.stem.replace("_", " ").title()

            # Try to extract summary from the first paragraph after title
            in_summary = False
            summary_lines = []

            for line in lines:
                line = line.strip()
                if line.startswith("# ") and not in_summary:
                    in_summary = True
                    continue
                elif in_summary and line and not line.startswith("#"):
                    summary_lines.append(line)
                elif in_summary and line.startswith("#"):
                    break
                elif in_summary and summary_lines and not line:
                    break

            if summary_lines:
                metadata["summary"] = " ".join(summary_lines)

            # Removed tag extraction logic from here
            # # Try to extract tags from content
            # for line in lines:
            #     if "tags:" in line.lower() or "keywords:" in line.lower():
            #         tag_part = line.split(":", 1)[1].strip()
            #         tags = [t.strip() for t in tag_part.split(",")]
            #         metadata["tags"] = [t for t in tags if t]
            #         break

    except Exception as e:
        logger.warning(f"Error extracting metadata from {file_path}: {e}")

    return metadata

def index_patterns(base_path: str = "./patterns", descriptions_file: str = "./pattern_descriptions.json") -> Dict[str, PatternMetadata]:
    """
    Walks folders under base_path, reads system.md, gets tags from descriptions file,
    and builds a searchable map keyed by slug.

    Args:
        base_path: Root directory containing pattern folders
        descriptions_file: Path to the JSON file containing pattern descriptions and tags

    Returns:
        Dict mapping slugs to PatternMetadata objects
    """
    logger.info(f"Indexing patterns in {base_path}")
    index = {}
    base_path = Path(base_path)
    descriptions_path = Path(descriptions_file)
    descriptions_lookup = {}

    # Load pattern descriptions for tag lookup
    if descriptions_path.exists():
        try:
            with open(descriptions_path, "r", encoding="utf-8") as f:
                loaded_descriptions = json.load(f)
                descriptions_lookup = {
                    item['patternName']: item 
                    for item in loaded_descriptions.get('patterns', []) 
                    if 'patternName' in item
                }
            logger.info(f"Loaded {len(descriptions_lookup)} descriptions from {descriptions_path}")
        except Exception as e:
            logger.error(f"Error loading or parsing {descriptions_path}: {e}. Tags will not be indexed.")
    else:
        logger.warning(f"Descriptions file not found at {descriptions_path}. Tags will not be indexed.")

    if not base_path.exists():
        logger.warning(f"Patterns directory {base_path} does not exist")
        return {}
    
    try:
        # Walk through immediate subdirectories of base_path
        for item in base_path.iterdir():
            if not item.is_dir():
                continue
            
            slug = item.name
            pattern_dir = item
            
            # Check for system.md (primary content file)
            system_md_path = pattern_dir / "system.md"
            user_md_path = pattern_dir / "user.md"
            
            # Skip directories without system.md
            if not system_md_path.exists():
                logger.debug(f"Skipping {slug}: No system.md found")
                continue
            
            # Extract metadata from system.md
            metadata = extract_metadata_from_markdown(system_md_path)
            
            # Get tags from the loaded descriptions
            pattern_desc_data = descriptions_lookup.get(slug, {})
            tags = pattern_desc_data.get("tags", [])

            # Create pattern metadata entry
            pattern_meta = PatternMetadata(
                slug=slug,
                title=metadata["title"] or slug.replace("_", " ").title(),
                summary=metadata["summary"],
                tags=tags, # Assign tags from descriptions file
                full_path=pattern_dir,
                system_md_path=system_md_path if system_md_path.exists() else None,
                user_md_path=user_md_path if user_md_path.exists() else None
            )
            
            index[slug] = pattern_meta
            logger.debug(f"Indexed pattern: {slug}")
    
    except Exception as e:
        logger.error(f"Error indexing patterns: {e}")
    
    logger.info(f"Indexed {len(index)} patterns")
    return index

def save_index_to_file(index: Dict[str, PatternMetadata], output_path: Path) -> bool:
    """
    Save the pattern index to a JSON file for later fast loading.
    
    Args:
        index: Pattern index mapping slugs to metadata
        output_path: Path to save the index file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Convert to serializable format
        serializable_index = {}
        for slug, metadata in index.items():
            serializable_index[slug] = {
                "slug": metadata.slug,
                "title": metadata.title,
                "summary": metadata.summary,
                "tags": metadata.tags,
                "full_path": str(metadata.full_path),
                "system_md_path": str(metadata.system_md_path) if metadata.system_md_path else None,
                "user_md_path": str(metadata.user_md_path) if metadata.user_md_path else None
            }
        
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(serializable_index, f, indent=2)
        
        logger.info(f"Pattern index saved to {output_path}")
        return True
    
    except Exception as e:
        logger.error(f"Error saving pattern index: {e}")
        return False

def load_index_from_file(input_path: Path) -> Dict[str, PatternMetadata]:
    """
    Load a previously saved pattern index from a JSON file.
    
    Args:
        input_path: Path to the index file
        
    Returns:
        Dict mapping slugs to PatternMetadata objects
    """
    try:
        if not input_path.exists():
            logger.warning(f"Index file {input_path} does not exist")
            return {}
        
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Convert back to PatternMetadata objects
        index = {}
        for slug, item in data.items():
            index[slug] = PatternMetadata(
                slug=item["slug"],
                title=item["title"],
                summary=item["summary"],
                tags=item["tags"],
                full_path=Path(item["full_path"]),
                system_md_path=Path(item["system_md_path"]) if item["system_md_path"] else None,
                user_md_path=Path(item["user_md_path"]) if item["user_md_path"] else None
            )
        
        logger.info(f"Loaded pattern index with {len(index)} patterns from {input_path}")
        return index
    
    except Exception as e:
        logger.error(f"Error loading pattern index: {e}")
        return {}

def get_index(base_path: str = "./patterns", index_path: Optional[Path] = None, force_rebuild: bool = False) -> Dict[str, PatternMetadata]:
    """
    Get a pattern index, loading from cache if available or rebuilding if necessary.
    
    Args:
        base_path: Root directory containing pattern folders
        index_path: Path to the index cache file
        force_rebuild: Whether to force rebuilding the index even if cache exists
        
    Returns:
        Dict mapping slugs to PatternMetadata objects
    """
    # If index_path is not provided, use default in data directory
    if index_path is None:
        data_dir = Path("./data")
        data_dir.mkdir(exist_ok=True)
        index_path = data_dir / "pattern_index.json"
    
    # Load from cache if available and not forcing rebuild
    if index_path.exists() and not force_rebuild:
        index = load_index_from_file(index_path)
        if index:
            return index
    
    # Build index and save to cache
    index = index_patterns(base_path)
    if index:
        save_index_to_file(index, index_path)
    
    return index

def find_in_index(query: str, index: Dict[str, PatternMetadata], fuzzy_threshold: int = 65) -> List[Tuple[int, PatternMetadata]]:
    """
    Search for patterns in the index using fuzzy matching.

    Args:
        query: Search query (can be slug, title, or tag)
        index: Pattern index to search in
        fuzzy_threshold: Minimum score (0-100) to include in results

    Returns:
        List of (score, metadata) tuples sorted by score (highest first)
    """
    results = []
    query_lower = query.lower()

    for slug, metadata in index.items():
        scores = []

        # Score against slug
        scores.append(fuzz.partial_ratio(query_lower, slug.lower()))
        scores.append(fuzz.token_set_ratio(query_lower, slug.lower()))

        # Score against title
        if metadata.title:
            scores.append(fuzz.partial_ratio(query_lower, metadata.title.lower()))
            scores.append(fuzz.token_set_ratio(query_lower, metadata.title.lower()))

        # Score against summary
        if metadata.summary:
            scores.append(fuzz.partial_ratio(query_lower, metadata.summary.lower()))
            # token_set_ratio can be slow on long summaries, consider omitting or adjusting
            # scores.append(fuzz.token_set_ratio(query_lower, metadata.summary.lower())) 

        # Score against individual tags
        if metadata.tags:
            for tag in metadata.tags:
                scores.append(fuzz.ratio(query_lower, tag.lower())) # Exact tag match bonus
                scores.append(fuzz.token_set_ratio(query_lower, tag.lower()))
        
        # Use the maximum score achieved across all fields
        max_score = max(scores) if scores else 0

        # Only include if score meets threshold
        if max_score >= fuzzy_threshold:
            results.append((max_score, metadata))

    # Sort by score (highest first)
    return sorted(results, key=lambda x: x[0], reverse=True)

def slug_to_content(slug: str, base_path: str = "./patterns") -> Optional[str]:
    """
    Load a pattern's system.md content by slug.
    
    Args:
        slug: Pattern slug (folder name)
        base_path: Root directory containing pattern folders
        
    Returns:
        str: The pattern content, or None if not found
    """
    pattern_path = Path(base_path) / slug / "system.md"
    if not pattern_path.exists():
        return None
    
    try:
        with open(pattern_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error loading pattern content: {e}")
        return None

def resolve_slug(slug_or_query: str, base_path: str = "./patterns") -> Optional[Tuple[str, str]]:
    """
    Resolve a slug or query to a pattern slug and content.
    Falls back to fuzzy matching if exact match not found.
    
    Args:
        slug_or_query: Slug or search query
        base_path: Root directory containing pattern folders
        
    Returns:
        Tuple of (slug, content) if found, None otherwise
    """
    # Get index
    index = get_index(base_path)
    
    # Try exact match first (still useful for direct slug access)
    if slug_or_query in index:
        content = slug_to_content(slug_or_query, base_path)
        if content:
            # Return perfect score for direct match
            # Note: This function returns slug/content, not score. 
            # The search function uses find_in_index which now returns fuzzy scores.
            return (slug_or_query, content)
    
    # Try fuzzy search using the updated find_in_index
    results = find_in_index(slug_or_query, index) # Now uses fuzzy matching
    if results:
        top_match_score, top_match_metadata = results[0]
        content = slug_to_content(top_match_metadata.slug, base_path)
        if content:
            return (top_match_metadata.slug, content)
    
    return None

def get_similar_slugs(query: str, base_path: str = "./patterns", limit: int = 5) -> List[str]:
    """
    Get a list of similar slugs for a query using fuzzy search.
    
    Args:
        query: Search query
        base_path: Root directory containing pattern folders
        limit: Maximum number of results
        
    Returns:
        List of similar slugs
    """
    index = get_index(base_path)
    results = find_in_index(query, index) # Now uses fuzzy matching
    return [result[1].slug for result in results[:limit]]