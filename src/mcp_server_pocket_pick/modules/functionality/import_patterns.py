import json
import sqlite3
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from ..data_types import ImportPatternsCommand, PocketItem
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

def import_patterns(command: ImportPatternsCommand) -> List[PocketItem]:
    """
    Import Themes Fabric patterns from descriptions and extracts JSON files
    into the Pocket Pick database.
    
    Args:
        command: ImportPatternsCommand with descriptions_path, extracts_path and db_path
        
    Returns:
        List[PocketItem]: The newly created items
    """
    logger.info(f"Importing patterns from {command.descriptions_path} and {command.extracts_path}")
    
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
            
            # Format the text content for storage
            text_parts = [
                f"# {name}",
                f"\n## Description\n{desc}",
                f"\n## Pattern Extract\n{extract}"
            ]
            
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
            logger.info(f"Imported pattern: {name} with ID: {item_id}")
        
        # Commit transaction
        db.commit()
        
        return imported_items
    except Exception as e:
        logger.error(f"Error importing patterns: {e}")
        db.rollback()
        raise
    finally:
        db.close()