import uuid
import json
from datetime import datetime
import logging
from ..data_types import AddCommand, PocketItem
from ..init_db import normalize_tags
from ..connection_pool import get_db_connection
from ..embeddings import EmbeddingGenerator, serialize_embedding

logger = logging.getLogger(__name__)

def add(command: AddCommand) -> PocketItem:
    """
    Add a new item to the pocket pick database
    
    Args:
        command: AddCommand with text, tags and db_path
        
    Returns:
        PocketItem: The newly created item
    """
    # Normalize tags
    normalized_tags = normalize_tags(command.tags)
    
    # Generate a unique ID
    item_id = str(uuid.uuid4())
    
    # Get current timestamp
    timestamp = datetime.now()
    
    # Use connection pool for better performance
    with get_db_connection(command.db_path) as conn:
        try:
            # Serialize tags to JSON
            tags_json = json.dumps(normalized_tags)
            
            # Generate embedding for the text
            embedding = None
            embedding_blob = None
            embedding_updated = None
            
            try:
                embedding_generator = EmbeddingGenerator()
                embedding = embedding_generator.generate_embedding(command.text)
                embedding_blob = serialize_embedding(embedding)
                embedding_updated = timestamp.isoformat()
                logger.debug(f"Generated embedding for new item: {item_id}")
            except Exception as e:
                logger.warning(f"Failed to generate embedding for new item: {e}")
            
            # Insert item with embedding
            conn.execute("""
                INSERT INTO POCKET_PICK 
                (id, created, text, tags, embedding, embedding_model, embedding_updated) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                item_id, 
                timestamp.isoformat(), 
                command.text, 
                tags_json,
                embedding_blob,
                'all-MiniLM-L6-v2',
                embedding_updated
            ))
            
            # Commit transaction
            conn.commit()
            
            # Return created item
            return PocketItem(
                id=item_id,
                created=timestamp,
                text=command.text,
                tags=normalized_tags
            )
        except Exception as e:
            logger.error(f"Error adding item: {e}")
            raise