# tests/functionality/test_fabric_integration_with_bodies.py

import json
import sqlite3
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

from mcp_server_pocket_pick.modules.data_types import ImportPatternsWithBodiesCommand
from mcp_server_pocket_pick.modules.functionality.import_patterns_with_bodies import import_patterns_with_bodies, read_pattern_body, sanitize_markdown

# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_descriptions(tmp_path):
    data = {
        "patterns": [
            {
                "patternName": "alpha",
                "description": "Alpha pattern description.",
                "tags": ["tag1", "tag2"]
            },
            {
                "patternName": "beta",
                "description": "Beta pattern description.",
                "tags": []
            }
        ]
    }
    p = tmp_path / "pattern_descriptions.json"
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(data, f)
    return p

@pytest.fixture
def sample_extracts(tmp_path):
    data = {
        "alpha": "First 500 words excerpt for alpha...",
        "beta": "Excerpt for beta..."
    }
    p = tmp_path / "pattern_extracts.json"
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(data, f)
    return p

@pytest.fixture
def patterns_root(tmp_path):
    # Create pattern directories with system.md files
    alpha_dir = tmp_path / "alpha"
    alpha_dir.mkdir()
    alpha_system_md = alpha_dir / "system.md"
    alpha_system_md.write_text("""
    # Alpha Pattern System.md
    
    This is the full body content for Alpha pattern.
    
    ## Details
    
    More details about Alpha pattern goes here.
    """)
    
    # Beta directory without system.md
    beta_dir = tmp_path / "beta"
    beta_dir.mkdir()
    
    return tmp_path

@pytest.fixture
def temp_db(tmp_path):
    return tmp_path / "test_pocket.db"

# ─── Tests for Utility Functions ──────────────────────────────────────────────

def test_sanitize_markdown():
    # Test with mixed line endings
    mixed_endings = "Line 1\r\nLine 2\nLine 3\r\n"
    sanitized = sanitize_markdown(mixed_endings)
    assert "\r\n" not in sanitized
    assert sanitized == "Line 1\nLine 2\nLine 3"
    
    # Test with null characters
    with_nulls = "Text with \0 null \0 characters"
    sanitized = sanitize_markdown(with_nulls)
    assert "\0" not in sanitized
    
    # Test with extra whitespace
    with_whitespace = "  Text with extra whitespace  \n  "
    sanitized = sanitize_markdown(with_whitespace)
    assert sanitized == "Text with extra whitespace"

def test_read_pattern_body(patterns_root):
    # Test for existing system.md
    body = read_pattern_body(patterns_root, "alpha")
    assert body is not None
    assert "full body content for Alpha pattern" in body
    
    # Test for non-existing system.md
    body = read_pattern_body(patterns_root, "beta")
    assert body is None
    
    # Test for non-existing pattern directory
    body = read_pattern_body(patterns_root, "non_existent")
    assert body is None

# ─── Tests for Import With Bodies ────────────────────────────────────────────

def test_import_patterns_with_bodies(sample_descriptions, sample_extracts, patterns_root, temp_db):
    # Create command
    command = ImportPatternsWithBodiesCommand(
        patterns_root=patterns_root,
        descriptions_path=sample_descriptions,
        extracts_path=sample_extracts,
        db_path=temp_db
    )
    
    # Run import
    results = import_patterns_with_bodies(command)
    
    # Verify results
    assert len(results) == 2
    
    # Verify DB and contents
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    # Two rows inserted
    cursor.execute("SELECT COUNT(*) FROM POCKET_PICK;")
    count = cursor.fetchone()[0]
    assert count == 2
    
    # Check Alpha entry (should have pattern body)
    cursor.execute("SELECT text FROM POCKET_PICK WHERE text LIKE '%alpha%';")
    alpha_text = cursor.fetchone()[0]
    assert "## Pattern Body" in alpha_text
    assert "full body content for Alpha pattern" in alpha_text
    
    # Check Beta entry (should NOT have pattern body)
    cursor.execute("SELECT text FROM POCKET_PICK WHERE text LIKE '%beta%';")
    beta_text = cursor.fetchone()[0]
    assert "## Pattern Body" not in beta_text
    
    conn.close()

def test_import_patterns_with_non_existent_patterns_dir(sample_descriptions, sample_extracts, tmp_path, temp_db):
    non_existent_dir = tmp_path / "non_existent"
    
    # Create command with non-existent patterns directory
    command = ImportPatternsWithBodiesCommand(
        patterns_root=non_existent_dir,
        descriptions_path=sample_descriptions,
        extracts_path=sample_extracts,
        db_path=temp_db
    )
    
    # Run import (should still work, but without pattern bodies)
    results = import_patterns_with_bodies(command)
    
    # Verify results
    assert len(results) == 2
    
    # Verify no pattern bodies were included
    for item in results:
        assert "## Pattern Body" not in item.text