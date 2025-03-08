import sqlite3
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def init_db(db_path: Path) -> sqlite3.Connection:
    """Initialize SQLite database with POCKET_PICK table"""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Initializing database at {db_path}")
    db = sqlite3.connect(str(db_path))
    
    # Enable foreign keys
    db.execute("PRAGMA foreign_keys = ON")
    
    # Create the POCKET_PICK table
    db.execute("""
    CREATE TABLE IF NOT EXISTS POCKET_PICK (
        id TEXT PRIMARY KEY,
        created TIMESTAMP NOT NULL,
        text TEXT NOT NULL,
        tags TEXT NOT NULL
    )
    """)
    
    # Create indexes for efficient searching
    db.execute("CREATE INDEX IF NOT EXISTS idx_pocket_pick_created ON POCKET_PICK(created)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_pocket_pick_text ON POCKET_PICK(text)")
    
    # Commit changes
    db.commit()
    
    return db

def normalize_tag(tag: str) -> str:
    """
    Normalize tags:
    - lowercase
    - trim whitespace
    - replace spaces and underscores with dashes
    """
    tag = tag.lower().strip()
    return tag.replace(' ', '-').replace('_', '-')

def normalize_tags(tags: list[str]) -> list[str]:
    """Apply normalization to a list of tags"""
    return [normalize_tag(tag) for tag in tags]