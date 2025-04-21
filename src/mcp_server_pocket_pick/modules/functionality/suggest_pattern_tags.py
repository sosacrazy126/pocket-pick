import logging
import json
from pathlib import Path
from typing import List, Dict, Any

from ..data_types import SuggestPatternTagsCommand, PocketItem
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

def import_anthropic():
    """
    Import the anthropic module if available.
    This function is extracted to make testing easier.
    """
    try:
        import anthropic
        return anthropic
    except ImportError as e:
        logger.warning(f"Could not import anthropic: {e}")
        raise

def suggest_pattern_tags(command: SuggestPatternTagsCommand) -> List[str]:
    """
    Suggest tags for a Themes Fabric pattern using LLM analysis.
    
    This function uses Claude to analyze pattern content and suggest
    relevant tags based on the content.
    
    Args:
        command: SuggestPatternTagsCommand with pattern_path, num_tags, and optional existing_tags
        
    Returns:
        List[str]: The suggested tags
    """
    logger.info(f"Suggesting tags for pattern: {command.pattern_path}")
    
    # Load the pattern content
    try:
        with open(command.pattern_path, "r", encoding="utf-8") as f:
            pattern_content = f.read()
    except Exception as e:
        logger.error(f"Error reading pattern file: {e}")
        raise
    
    # Set up content to analyze
    content_to_analyze = pattern_content
    
    # Use the Claude API to suggest tags
    try:
        # Import the anthropic client
        anthropic = import_anthropic()
        
        client = anthropic.Anthropic()
        
        # Instructions for tag generation
        prompt = f"""
        Analyze the following document and suggest {command.num_tags} relevant tags for it. 
        These tags should capture important concepts, themes, and topics in the document.
        
        The tags should be:
        - Single words or short phrases
        - Lowercase
        - Relevant to thematic frameworks, cognition, consciousness, cultural evolution, etc.
        - Helpful for categorizing and finding this document later
        
        Document:
        ---
        {content_to_analyze}
        ---
        
        Please respond ONLY with a comma-separated list of tags, nothing else.
        
        Example format: consciousness, emergence, systems-thinking, ritual, practice, embodiment
        """
        
        # If there are existing tags, add them to the prompt
        if command.existing_tags:
            prompt += f"\n\nExisting tags (consider these but suggest new ones too): {', '.join(command.existing_tags)}"
        
        # Call Claude
        message = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1024,
            temperature=0.7,
            system="You are a thoughtful, precise tagger of complex documents. Your job is to generate relevant, insightful tags.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract the suggested tags from the response
        raw_tags = message.content[0].text.strip()
        
        # Split by commas and clean up
        suggested_tags = [tag.strip() for tag in raw_tags.split(',')]
        
        # Normalize the tags
        normalized_tags = normalize_tags(suggested_tags)
        
        logger.info(f"Generated {len(normalized_tags)} suggested tags")
        return normalized_tags
        
    except ImportError:
        logger.error("Anthropic package not installed. Falling back to basic tag extraction.")
        # Fallback: Extract potential tags from content using simple keyword identification
        # This is a very basic approach and won't be as good as LLM-based suggestion
        common_theme_keywords = [
            "consciousness", "emergence", "systems", "thinking", "ritual", 
            "practice", "embodiment", "evolution", "cognition", "hyperorganism",
            "collaboration", "coordination", "symbolic", "language", "meaning",
            "intentionality", "agency", "intelligence", "collective", "network"
        ]
        
        # Check which keywords appear in the content
        suggested_tags = []
        for keyword in common_theme_keywords:
            if keyword.lower() in content_to_analyze.lower():
                suggested_tags.append(keyword)
                
        # Take only the requested number
        return suggested_tags[:command.num_tags]
    
    except Exception as e:
        logger.error(f"Error suggesting tags: {e}")
        # Return some basic default tags as fallback
        return ["themes-fabric", "pattern", "needs-tagging"]