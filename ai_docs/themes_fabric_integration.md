# Themes Fabric Integration for Pocket Pick

This guide explains how to use the Themes Fabric pattern system with Pocket Pick through the Claude MCP integration.

## Overview

The Themes Fabric integration allows you to:
- Import pattern descriptions and extracts into Pocket Pick
- Import full pattern bodies from system.md files
- Get AI-suggested tags for your patterns
- Search and retrieve patterns using tags and text search
- Access pattern content directly through Claude conversations

## Requirements

- Python 3.10 or higher (required for match-case syntax)
- UV package manager (recommended)
- Anthropic API access for AI-powered tag suggestions (optional)

## Setup

1. Make sure you have Pocket Pick set up and registered as an MCP server for Claude:

```bash
# Using UV (recommended)
claude mcp add pocket-pick -- \
    uv --directory /path/to/pocket-pick-codebase \
    run mcp-server-pocket-pick

# Or using Python from the virtual environment
claude mcp add pocket-pick -- \
    /path/to/pocket-pick-codebase/.venv/bin/python -m mcp_server_pocket_pick
```

2. Prepare your Themes Fabric files:
   - `pattern_descriptions.json`: Contains pattern metadata and descriptions
   - `pattern_extracts.json`: Contains the actual pattern extract text
   - `patterns/` directory: Contains subdirectories for each pattern, with pattern bodies in `system.md` files

## Importing Patterns

### Basic Import (Descriptions and Extracts Only)

You can import your Themes Fabric patterns through Claude by simply asking:

```
Import Themes Fabric patterns from the descriptions file at pattern_descriptions.json and extracts file at pattern_extracts.json
```

Claude will use the `pocket_import_patterns` MCP tool to import these patterns into your Pocket Pick database.

### Full Pattern Import (Including Pattern Bodies)

To import patterns with their full bodies from system.md files:

```
Import Themes Fabric patterns with bodies from the patterns directory at patterns/, descriptions file at pattern_descriptions.json, and extracts file at pattern_extracts.json
```

This will use the `pocket_import_patterns_with_bodies` MCP tool to import the complete patterns with their full content.

### Import Command Structure

The import commands expect:
- `patterns_root` (for full import): Path to the patterns directory containing pattern subdirectories
- `descriptions_path`: Path to the pattern_descriptions.json file
- `extracts_path`: Path to the pattern_extracts.json file

## AI-Powered Tag Suggestions

You can get AI-generated tag suggestions for your pattern files:

```
Suggest tags for the pattern at patterns/agility_story/system.md
```

This uses Claude (or a fallback keyword system) to analyze the pattern content and suggest relevant tags.

The tag suggester accepts these parameters:
- `pattern_path`: Path to the pattern file to analyze
- `num_tags` (optional): Number of tags to suggest (default: 10)
- `existing_tags` (optional): List of existing tags to consider

## Working with Patterns

Once imported, your patterns can be accessed using any of the standard Pocket Pick commands:

### Finding Patterns by Tag

```
Find pocket pick items with the tags: ritual, cognition
```

### Searching Pattern Content

```
Find items containing "consciousness" using full text search
```

### Getting a Specific Pattern

```
List all pocket pick items with the tag "themes-fabric"
```

## Slug-Based Pattern Access

The slug-based pattern access allows you to directly retrieve patterns by their folder name (slug), with fuzzy matching fallback:

### Searching for Patterns by Slug, Title, or Content

```
Search for patterns with query "analysis"
```

This uses the `pocket_pattern_search` MCP tool to find patterns matching the query in slugs, titles, or content, and returns a list of matches with their metadata.

### Getting a Pattern by Slug

```
Get pattern with slug "analyze_paper"
```

This uses the `pocket_get_pattern` MCP tool to retrieve a specific pattern by its slug. If the exact slug is not found, it suggests similar slugs that might match what you're looking for.

### Features of Slug-Based Access

- **Human-readable identifiers**: Use folder names instead of opaque UUIDs
- **Fuzzy matching**: Find patterns even with partial or approximate slugs
- **Content-aware search**: Find patterns based on their content, not just metadata
- **Ranked results**: Get the most relevant matches first
- **Helpful suggestions**: When a pattern is not found, get suggestions for similar patterns

## Testing the Integration

Make sure to use the correct Python version when testing:

```bash
# Run all tests (always use Python 3.10+)
.venv/bin/python -m pytest

# Run just the Themes Fabric integration tests
.venv/bin/python -m pytest src/mcp_server_pocket_pick/tests/functionality/test_fabric_integration.py
.venv/bin/python -m pytest src/mcp_server_pocket_pick/tests/functionality/test_fabric_integration_with_bodies.py
```

## Pattern Structure

Each imported pattern is stored with the following structure:

```
# Pattern Name

## Description
The pattern description text...

## Pattern Extract
The actual pattern extract content...

## Pattern Body
The full pattern body from system.md (if available)...

## Additional Metadata
- **key**: value
- **otherKey**: otherValue
```

All patterns are automatically tagged with `themes-fabric` plus any additional tags specified in the pattern description.

## Example Workflow

Here's a complete workflow example:

1. Import patterns with full bodies:
   ```
   Import Themes Fabric patterns with bodies from the patterns directory at patterns/, descriptions file at pattern_descriptions.json, and extracts file at pattern_extracts.json
   ```

2. Get tag suggestions for a new pattern:
   ```
   Suggest tags for the pattern at patterns/analyze_claims/system.md with 15 tags
   ```

3. Add a pattern with suggested tags:
   ```
   Add the file patterns/analyze_threat_report/system.md as a pocket pick item with tags: cybersecurity, analysis, threat-modeling
   ```

4. List available patterns:
   ```
   List all pocket pick items with the tag "themes-fabric"
   ```

5. Find specific patterns:
   ```
   Find pocket pick items with the tags: analysis, cognitive
   ```

6. Use a pattern in a creative context:
   ```
   Find items containing "analysis" and help me incorporate these ideas into a methodology for assessing impact
   ```

## Advanced Usage

You can combine Pocket Pick's search capabilities with Claude's reasoning to analyze patterns:

```
Find all items tagged with "analysis" and summarize the common themes between them
```

Or create new content based on pattern combinations:

```
Find items containing "threat" and "intelligence" and create a framework for a security analysis procedure
```

## Extending the Integration

This integration can be extended with additional features such as:
- Bidirectional sync to update local files
- Custom visualization tools for pattern relationships

Refer to the main Pocket Pick documentation for more details on the underlying functionality.