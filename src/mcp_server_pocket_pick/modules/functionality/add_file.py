import sqlite3
import uuid
import json
from datetime import datetime
from pathlib import Path
import logging
from ..data_types import AddFileCommand, PocketItem
from ..init_db import init_db, normalize_tags

logger = logging.getLogger(__name__)

def add_file(command: AddFileCommand) -> PocketItem:
    """
    Add a new item to the pocket pick database from a file
    
    Args:
        command: AddFileCommand with file_path, tags and db_path
        
    Returns:
        PocketItem: The newly created item
    """
    # Read the file content
    try:
        file_path = Path(command.file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception as e:
        logger.error(f"Error reading file {command.file_path}: {e}")
        raise
    
    # Normalize tags
    normalized_tags = normalize_tags(command.tags)
    
    # Generate a unique ID
    item_id = str(uuid.uuid4())
    
    # Get current timestamp
    timestamp = datetime.now()
    
    # Connect to database
    db = init_db(command.db_path)
    
    try:
        # Serialize tags to JSON
        tags_json = json.dumps(normalized_tags)
        
        # Insert item
        db.execute(
            "INSERT INTO POCKET_PICK (id, created, text, tags) VALUES (?, ?, ?, ?)",
            (item_id, timestamp.isoformat(), text, tags_json)
        )
        
        # Commit transaction
        db.commit()
        
        # Return created item
        return PocketItem(
            id=item_id,
            created=timestamp,
            text=text,
            tags=normalized_tags
        )
    except Exception as e:
        logger.error(f"Error adding item from file: {e}")
        raise
    finally:
        db.close()