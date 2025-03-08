import sqlite3
import json
from datetime import datetime
from typing import List
import logging
import re
from ..data_types import FindCommand, PocketItem
from ..init_db import init_db, normalize_tags

logger = logging.getLogger(__name__)

def find(command: FindCommand) -> List[PocketItem]:
    """
    Find items in the pocket pick database matching the search criteria
    
    Args:
        command: FindCommand with search parameters
        
    Returns:
        List[PocketItem]: List of matching items
    """
    # Normalize tags
    normalized_tags = normalize_tags(command.tags) if command.tags else []
    
    # Connect to database
    db = init_db(command.db_path)
    
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
                # Split the search text into words and search for each word
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
        if normalized_tags:
            # Find items that have all the specified tags
            # We need to check if each tag exists in the JSON array
            tag_clauses = []
            for tag in normalized_tags:
                tag_clauses.append("tags LIKE ?")
                # Use JSON substring matching, looking for the tag surrounded by quotes and commas or brackets
                params.append(f"%\"{tag}\"%")
            
            where_clauses.append(f"({' AND '.join(tag_clauses)})")
        
        # Construct the full query
        if where_clauses:
            query += f" WHERE {' AND '.join(where_clauses)}"
        
        # Apply limit
        query += f" ORDER BY created DESC LIMIT {command.limit}"
        
        # Execute query
        cursor = db.execute(query, params)
        
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
    finally:
        db.close()