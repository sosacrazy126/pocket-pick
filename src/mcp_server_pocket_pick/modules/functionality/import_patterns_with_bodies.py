import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from ..data_types import ImportPatternsWithBodiesCommand, PocketItem
from ..init_db import init_db, normalize_tags

logger = logging.getLogger(__name__)

def load_json(path: Path) -> Dict[str, Any]:
    """Load JSON data from a file"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading JSON from {path}: {e}")
        raise

def sanitize_markdown(markdown_content: str) -> str:
    """
    Sanitize markdown content for safe storage and retrieval.
    
    Args:
        markdown_content: The raw markdown content
        
    Returns:
        str: Sanitized markdown
    """
    # Basic sanitization (can be extended as needed)
    sanitized = markdown_content.strip()
    
    # Ensure consistent line endings
    sanitized = sanitized.replace('\r\n', '\n')
    
    # Remove any null characters or other problematic chars
    sanitized = sanitized.replace('\0', '')
    
    return sanitized

def read_pattern_body(patterns_root: Path, pattern_name: str) -> Optional[str]:
    """
    Read a pattern body from the system.md file in the pattern directory.
    
    Args:
        patterns_root: Root directory containing pattern folders
        pattern_name: Name of the pattern
        
    Returns:
        Optional[str]: The pattern body if found, None otherwise
    """
    # Build path to the system.md file
    pattern_dir = patterns_root / pattern_name
    system_md_path = pattern_dir / "system.md"
    
    # Check if the file exists
    if not system_md_path.exists():
        logger.warning(f"No system.md found for pattern '{pattern_name}' at {system_md_path}")
        return None
    
    # Read and sanitize the file content
    try:
        with open(system_md_path, "r", encoding="utf-8") as f:
            content = f.read()
        return sanitize_markdown(content)
    except Exception as e:
        logger.error(f"Error reading system.md for pattern '{pattern_name}': {e}")
        return None

def import_patterns_with_bodies(command: ImportPatternsWithBodiesCommand) -> List[PocketItem]:
    """
    Import Themes Fabric patterns from descriptions and extracts JSON files,
    including full pattern bodies from system.md files.
    
    Args:
        command: ImportPatternsWithBodiesCommand with patterns_root, descriptions_path, extracts_path and db_path
        
    Returns:
        List[PocketItem]: The newly created items
    """
    logger.info(f"Importing patterns with bodies from {command.patterns_root}")
    
    # Load pattern descriptions and extracts
    descriptions = load_json(command.descriptions_path).get("patterns", [])
    extracts = load_json(command.extracts_path)
    
    # Connect to database
    db = init_db(command.db_path)
    
    imported_items = []
    
    try:
        for entry in descriptions:
            # Extract pattern details
            name = entry["patternName"]
            desc = entry.get("description", "[Description missing]")
            
            # Parse and normalize tags
            theme_tags = entry.get("tags", [])
            # Add default tags for all Themes Fabric patterns
            all_tags = ["themes-fabric"] + theme_tags
            normalized_tags = normalize_tags(all_tags)
            
            # Get extract if available
            extract = extracts.get(name, "")
            
            # Try to get the full pattern body
            pattern_body = read_pattern_body(command.patterns_root, name)
            
            # Format the text content for storage
            text_parts = [
                f"# {name}",
                f"\n## Description\n{desc}",
                f"\n## Pattern Extract\n{extract}"
            ]
            
            # Include the pattern body if available
            if pattern_body:
                text_parts.append(f"\n## Pattern Body\n{pattern_body}")
            
            # Add any additional metadata
            metadata = {k: v for k, v in entry.items() 
                       if k not in ["patternName", "description", "tags"]}
            
            if metadata:
                metadata_text = "\n## Additional Metadata\n"
                for key, value in metadata.items():
                    metadata_text += f"- **{key}**: {value}\n"
                text_parts.append(metadata_text)
            
            # Combine all sections
            full_text = "\n".join(text_parts)
            
            # Generate a unique ID and timestamp
            item_id = str(uuid.uuid4())
            timestamp = datetime.now()
            
            # Serialize tags to JSON
            tags_json = json.dumps(normalized_tags)
            
            # Insert item into database
            db.execute(
                "INSERT INTO POCKET_PICK (id, created, text, tags) VALUES (?, ?, ?, ?)",
                (item_id, timestamp.isoformat(), full_text, tags_json)
            )
            
            # Create PocketItem for return
            item = PocketItem(
                id=item_id,
                created=timestamp,
                text=full_text,
                tags=normalized_tags
            )
            
            imported_items.append(item)
            logger.info(f"Imported pattern with body: {name} with ID: {item_id}")
        
        # Commit transaction
        db.commit()
        
        return imported_items
    except Exception as e:
        logger.error(f"Error importing patterns with bodies: {e}")
        db.rollback()
        raise
    finally:
        db.close()