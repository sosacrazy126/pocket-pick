# tests/functionality/test_fabric_integration.py

import json
import sqlite3
import tempfile
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

from mcp_server_pocket_pick.modules.data_types import ImportPatternsCommand, SuggestPatternTagsCommand
from mcp_server_pocket_pick.modules.functionality.import_patterns import import_patterns
from mcp_server_pocket_pick.modules.functionality.suggest_pattern_tags import suggest_pattern_tags

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
def temp_db(tmp_path):
    return tmp_path / "test_pocket.db"

@pytest.fixture
def sample_pattern_file(tmp_path):
    content = """
    # Hyperorganism Pattern
    
    ## Introduction
    
    This pattern explores the concept of emergent collective intelligence and distributed cognition
    in social systems. The hyperorganism pattern recognizes that groups of individuals can form
    unified cognitive systems when they share information and coordinate effectively.
    
    ## Key Elements
    
    - Distributed cognition across individuals
    - Emergence of collective intelligence
    - Coordination through symbolic communication
    - Ritual practices that maintain shared context
    
    ## Applications
    
    The hyperorganism pattern can be applied to understand and design:
    - Collaborative research environments
    - Agile development teams
    - Cultural transmission of knowledge
    - Institutional coordination mechanisms
    """
    
    p = tmp_path / "hyperorganism.md"
    p.write_text(content)
    return p

# ─── Tests for Import Tool ─────────────────────────────────────────────────────

def test_import_patterns(sample_descriptions, sample_extracts, temp_db):
    # Create command
    command = ImportPatternsCommand(
        descriptions_path=sample_descriptions,
        extracts_path=sample_extracts,
        db_path=temp_db
    )
    
    # Run import
    results = import_patterns(command)
    
    # Verify results
    assert len(results) == 2
    assert results[0].tags[0] == "themes-fabric"
    assert "tag1" in results[0].tags
    assert "tag2" in results[0].tags
    
    # Verify DB and contents
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    # Table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='POCKET_PICK';")
    assert cursor.fetchone() is not None
    
    # Two rows inserted
    cursor.execute("SELECT COUNT(*) FROM POCKET_PICK;")
    count = cursor.fetchone()[0]
    assert count == 2
    
    # Check content and tags
    cursor.execute("SELECT text, tags FROM POCKET_PICK LIMIT 1;")
    text, tags_json = cursor.fetchone()
    
    # Text should contain pattern name, description and extract
    assert "alpha" in text
    assert "Alpha pattern description" in text
    assert "First 500 words excerpt" in text
    
    # Tags should include themes-fabric and original tags
    tags = json.loads(tags_json)
    assert "themes-fabric" in tags
    assert any(tag in ["tag1", "tag2"] for tag in tags)
    
    conn.close()

# ─── Tests for Tag Suggestion Tool ──────────────────────────────────────────────

def test_suggest_pattern_tags_fallback(sample_pattern_file, temp_db):
    # Force fallback by mocking the import to raise ImportError
    with patch('mcp_server_pocket_pick.modules.functionality.suggest_pattern_tags.import_anthropic', side_effect=ImportError("No module named 'anthropic'")):
        # Create command
        command = SuggestPatternTagsCommand(
            pattern_path=sample_pattern_file,
            num_tags=5,
            db_path=temp_db
        )
        
        # Run tag suggestion with fallback
        resp = suggest_pattern_tags(command)

        # Verify fallback tags (based on keywords in the content)
        assert len(resp.tags) > 0
        assert len(resp.tags) <= 5
        
        # Should find some of these keywords in the content
        expected_tags = ["cognition", "emergence", "collective", "intelligence", "systems"]
        assert any(tag in resp.tags for tag in expected_tags)

def test_suggest_pattern_tags_with_api(sample_pattern_file, temp_db):
    # Create mock objects for anthropic client
    mock_content = MagicMock()
    mock_content.text = "cognition, emergence, collective-intelligence, hyperorganism, ritual"
    
    mock_message = MagicMock()
    mock_message.content = [mock_content]
    
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message
    
    mock_anthropic_module = MagicMock()
    mock_anthropic_module.Anthropic.return_value = mock_client
    
    # Patch the import_anthropic function to return our mock
    with patch('mcp_server_pocket_pick.modules.functionality.suggest_pattern_tags.import_anthropic', return_value=mock_anthropic_module):
        # Create command
        command = SuggestPatternTagsCommand(
            pattern_path=sample_pattern_file,
            num_tags=5,
            db_path=temp_db
        )
        
        # Run tag suggestion with mocked API
        resp = suggest_pattern_tags(command)

        # Verify API-provided tags
        assert len(resp.tags) == 5
        assert "cognition" in resp.tags
        assert "emergence" in resp.tags
        assert "collective-intelligence" in resp.tags
        assert "hyperorganism" in resp.tags
        assert "ritual" in resp.tags
        
        # Verify that the API was called with appropriate arguments
        mock_client.messages.create.assert_called_once()
        # Check for key elements in the prompt
        call_args = mock_client.messages.create.call_args[1]
        assert "model" in call_args
        assert "messages" in call_args
        assert any("Analyze the following document" in msg.get("content", "") for msg in call_args["messages"])