import pytest
import tempfile
import os
from pathlib import Path
import json
import sqlite3
from ...modules.data_types import AddFileCommand, PocketItem
from ...modules.functionality.add_file import add_file

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
def temp_file_with_content():
    # Create a temporary file with content
    fd, path = tempfile.mkstemp()
    with os.fdopen(fd, 'w') as file:
        file.write("This is test content from a file")
    
    # Return the path as a string
    yield path
    
    # Clean up the temp file after test
    if os.path.exists(path):
        os.unlink(path)

def test_add_file_simple(temp_db_path, temp_file_with_content):
    # Create a command to add a file content
    command = AddFileCommand(
        file_path=temp_file_with_content,
        tags=["test", "file"],
        db_path=temp_db_path
    )
    
    # Add the item
    result = add_file(command)
    
    # Verify result is a PocketItem
    assert isinstance(result, PocketItem)
    assert result.text == "This is test content from a file"
    assert result.tags == ["test", "file"]
    assert result.id is not None
    
    # Verify item was added to the database
    db = sqlite3.connect(temp_db_path)
    cursor = db.execute("SELECT id, text, tags FROM POCKET_PICK")
    row = cursor.fetchone()
    
    assert row is not None
    assert row[0] == result.id
    assert row[1] == "This is test content from a file"
    
    # Verify tags were stored as JSON
    stored_tags = json.loads(row[2])
    assert stored_tags == ["test", "file"]
    
    # Verify no more rows exist
    assert cursor.fetchone() is None
    
    db.close()

def test_add_file_with_tag_normalization(temp_db_path, temp_file_with_content):
    # Create a command with tags that need normalization
    command = AddFileCommand(
        file_path=temp_file_with_content,
        tags=["FILE", "with space", "under_score"],
        db_path=temp_db_path
    )
    
    # Add the item
    result = add_file(command)
    
    # Verify tags were normalized
    assert result.tags == ["file", "with-space", "under-score"]
    
    # Verify in database
    db = sqlite3.connect(temp_db_path)
    cursor = db.execute("SELECT tags FROM POCKET_PICK")
    row = cursor.fetchone()
    
    stored_tags = json.loads(row[0])
    assert stored_tags == ["file", "with-space", "under-score"]
    
    db.close()

def test_add_file_nonexistent(temp_db_path):
    # Create a command with a nonexistent file
    command = AddFileCommand(
        file_path="/nonexistent/file/path.txt",
        tags=["test"],
        db_path=temp_db_path
    )
    
    # Expect FileNotFoundError when adding
    with pytest.raises(FileNotFoundError):
        add_file(command)