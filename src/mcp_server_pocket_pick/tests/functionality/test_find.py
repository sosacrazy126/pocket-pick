import pytest
import tempfile
import os
from pathlib import Path
import json
import sqlite3
from datetime import datetime
from ...modules.data_types import AddCommand, FindCommand, PocketItem
from ...modules.functionality.add import add
from ...modules.functionality.find import find
from ...modules.init_db import init_db

@pytest.fixture
def temp_db_path():
    # Create a temporary file path
    fd, path = tempfile.mkstemp()
    os.close(fd)
    
    # Return the path as a Path object
    yield Path(path)
    
    # Clean up the temp file after test
    if os.path.exists(path):
        os.unlink(path)

@pytest.fixture
def populated_db(temp_db_path):
    # Create sample items
    items = [
        {"text": "Python programming is fun", "tags": ["python", "programming", "fun"]},
        {"text": "SQL databases are powerful", "tags": ["sql", "database", "programming"]},
        {"text": "Testing code is important", "tags": ["testing", "code", "programming"]},
        {"text": "Regular expressions can be complex", "tags": ["regex", "programming", "advanced"]},
        {"text": "Learning new technologies is exciting", "tags": ["learning", "technology", "fun"]}
    ]
    
    # Add items to the database
    for item in items:
        command = AddCommand(
            text=item["text"],
            tags=item["tags"],
            db_path=temp_db_path
        )
        add(command)
    
    return temp_db_path

def test_find_substr(populated_db):
    # Search for "programming" substring
    command = FindCommand(
        text="programming",
        mode="substr",
        limit=10,
        db_path=populated_db
    )
    
    results = find(command)
    
    # Should match "Python programming is fun"
    assert len(results) == 1
    assert "Python programming is fun" in [r.text for r in results]

def test_find_fts(populated_db):
    # Search for "SQL powerful" (multiple words)
    command = FindCommand(
        text="SQL powerful",
        mode="fts",
        limit=10,
        db_path=populated_db
    )
    
    results = find(command)
    
    # Should match "SQL databases are powerful"
    assert len(results) == 1
    assert "SQL databases are powerful" in [r.text for r in results]

def test_find_glob(populated_db):
    # Search for text starting with "Test"
    command = FindCommand(
        text="Test*",
        mode="glob",
        limit=10,
        db_path=populated_db
    )
    
    results = find(command)
    
    # Should match "Testing code is important"
    assert len(results) == 1
    assert "Testing code is important" in [r.text for r in results]

def test_find_regex(populated_db):
    # Search for text containing "regular" (case insensitive)
    command = FindCommand(
        text=".*regular.*",
        mode="regex",
        limit=10,
        db_path=populated_db
    )
    
    results = find(command)
    
    # Should match "Regular expressions can be complex"
    assert len(results) == 1
    assert "Regular expressions can be complex" in [r.text for r in results]

def test_find_exact(populated_db):
    # Search for exact match
    command = FindCommand(
        text="Learning new technologies is exciting",
        mode="exact",
        limit=10,
        db_path=populated_db
    )
    
    results = find(command)
    
    # Should match exactly one item
    assert len(results) == 1
    assert results[0].text == "Learning new technologies is exciting"

def test_find_with_tags(populated_db):
    # Search for items with specific tags
    command = FindCommand(
        text="",  # No text search
        tags=["fun"],
        limit=10,
        db_path=populated_db
    )
    
    results = find(command)
    
    # Should match items with the "fun" tag
    assert len(results) == 2
    assert "Python programming is fun" in [r.text for r in results]
    assert "Learning new technologies is exciting" in [r.text for r in results]

def test_find_with_text_and_tags(populated_db):
    # Search for items with specific text and tags
    command = FindCommand(
        text="programming",
        mode="substr",
        tags=["fun"],
        limit=10,
        db_path=populated_db
    )
    
    results = find(command)
    
    # Should match items with "programming" text and "fun" tag
    assert len(results) == 1
    assert "Python programming is fun" in [r.text for r in results]

def test_find_limit(populated_db):
    # Search with limit
    command = FindCommand(
        text="",  # Match all
        limit=2,
        db_path=populated_db
    )
    
    results = find(command)
    
    # Should only return 2 items (due to limit)
    assert len(results) == 2