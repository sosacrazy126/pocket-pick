import pytest
from pathlib import Path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from mcp_server_pocket_pick.modules.functionality.suggest_pattern_tags import suggest_pattern_tags, SuggestPatternTagsResponse
from mcp_server_pocket_pick.modules.data_types import SuggestPatternTagsCommand

def test_file_not_found():
    cmd = SuggestPatternTagsCommand(pattern_path=Path('nonexistent.md'), num_tags=3)
    resp = suggest_pattern_tags(cmd)
    assert resp.tags == []
    assert resp.error is not None
    assert resp.source == 'fallback'

def test_fallback_keywords(tmp_path):
    # Write a pattern file with some known keywords
    pattern = """
    This pattern explores consciousness, emergence, and collective intelligence in ritual practice.
    """
    f = tmp_path / "pattern.md"
    f.write_text(pattern)
    cmd = SuggestPatternTagsCommand(pattern_path=f, num_tags=3)
    resp = suggest_pattern_tags(cmd)
    assert set(resp.tags) & {"consciousness", "emergence", "practice", "collective", "intelligence"}
    assert resp.source in ('fallback', 'ai')

def test_fallback_nltk(tmp_path):
    pattern = """
    This pattern is about learning, teaching, and the process of education and knowledge transfer.
    """
    f = tmp_path / "pattern.md"
    f.write_text(pattern)
    cmd = SuggestPatternTagsCommand(pattern_path=f, num_tags=3)
    resp = suggest_pattern_tags(cmd)
    assert len(resp.tags) > 0
    assert resp.source in ('ai', 'fallback')

def test_ai_path(monkeypatch, tmp_path):
    # Simulate Claude/Anthropic API
    class DummyMessage:
        def __init__(self, text):
            self.content = [type('obj', (), {'text': text})]
    class DummyAnthropic:
        class messages:
            @staticmethod
            def create(**kwargs):
                return DummyMessage('["ai_tag1", "ai_tag2", "ai_tag3"]')
    def fake_import_anthropic():
        return type('obj', (), {'Anthropic': lambda: DummyAnthropic})
    import mcp_server_pocket_pick.modules.functionality.suggest_pattern_tags as spt
    monkeypatch.setattr(spt, 'import_anthropic', fake_import_anthropic)
    pattern = "Pattern body for AI path."
    f = tmp_path / "pattern.md"
    f.write_text(pattern)
    cmd = SuggestPatternTagsCommand(pattern_path=f, num_tags=3)
    resp = spt.suggest_pattern_tags(cmd)
    assert resp.tags == ["ai_tag1", "ai_tag2", "ai_tag3"]
    assert resp.source == 'ai'
    assert resp.confidence == [0.8, 0.8, 0.8]
