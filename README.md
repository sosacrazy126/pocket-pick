# Pocket Pick (MCP Server)
> See how we used AI Coding, Claude Code, and MCP to build this tool on the [@IndyDevDan youtube channel](https://youtu.be/d-SyGA0Avtw).

As engineers we end up reusing ideas, patterns and code snippets all the time but keeping track of these snippets can be hard and remembering where you stored them can be even harder. What if the exact snippet or idea you were looking for was one prompt away?

With Anthropic's new MCP (Model Context Protocol) and a minimal portable database layer - we can solve this problem. Pocket Pick is your personal engineering knowledge base that lets you quickly store ideas, patterns and code snippets and gives you a DEAD SIMPLE text or tag based searching to quickly find them in the future.

<img src="./images/pocket-pick.png" alt="Pocket Pick" style="max-width: 600px;">

## Features

- **Personal Knowledge Base**: Store code snippets, information, and ideas
- **Tag-Based Organization**: Add tags to categorize and filter your knowledge
- **Flexible Search**: Find content using substring, full-text, glob, regex, or exact matching
- **MCP Integration**: Seamlessly works with Claude and other MCP-compatible AI assistants
- **SQLite Backend**: Fast, reliable, and portable database storage
- **Command-Line Interface**: Easy to use from the terminal
- **Themes Fabric Integration**: Import and manage pattern descriptions and extracts from Themes Fabric

## Installation

Install [uv](https://docs.astral.sh/uv/getting-started/installation/)

```bash
# Clone the repository
git clone https://github.com/indydevdan/pocket-pick.git
cd pocket-pick

# Install dependencies
uv sync
```

Usage from JSON format

Default Database for Claude Code

```json
{
    "command": "uv",
    "args": ["--directory", ".", "run", "mcp-server-pocket-pick"]
}
```

Custom Database for Claude Code

```json
{
    "command": "uv",
    "args": ["--directory", ".", "run", "mcp-server-pocket-pick", "--database", "./database.db"]
}
```

## Usage with Claude Code

```bash
# Add the pocket-pick server to Claude Code (if you're in the directory)
claude mcp add pocket-pick -- \
    uv --directory . \
    run mcp-server-pocket-pick

# Add the pocket-pick server to Claude Code
claude mcp add pocket-pick -- \
    uv --directory /path/to/pocket-pick-codebase \
    run mcp-server-pocket-pick

# With custom database location
claude mcp add pocket-pick -- \
    uv --directory /path/to/pocket-pick-codebase \
    run mcp-server-pocket-pick --database ./database.db

# List existing MCP servers - Validate that the server is running
claude mcp list

# Start claude code
claude
```

## Pocket Pick MCP Tools

The following MCP tools are available in Pocket Pick:

| Tool                 | Description                                  |
| -------------------- | -------------------------------------------- |
| `pocket_add`         | Add a new item to your knowledge base        |
| `pocket_add_file`    | Add a file's content to your knowledge base  |
| `pocket_find`        | Find items by text and/or tags               |
| `pocket_list`        | List all items, optionally filtered by tags  |
| `pocket_list_tags`   | List all tags with their counts              |
| `pocket_remove`      | Remove an item by ID                         |
| `pocket_get`         | Get a specific item by ID                    |
| `pocket_backup`      | Backup the database                          |
| `pocket_to_file_by_id` | Write an item's content to a file by its ID (requires absolute path) |
| `pocket_import_patterns` | Import Themes Fabric patterns from descriptions and extracts JSON files |
| `pocket_import_patterns_with_bodies` | Import Themes Fabric patterns with full pattern bodies from system.md files |
| `pocket_suggest_pattern_tags` | Use AI to suggest relevant tags for a Themes Fabric pattern file |

## Using with Claude

After setting up Pocket Pick as an MCP server for Claude Code, you can use it your conversations:

### Adding Items

Add items directly

```bash
Add "claude mcp list" as a pocket pick item. tags: mcp, claude, code
```

Add items from clipboard

```bash
pbpaste and create a pocket pick item with the following tags: python, algorithm, fibonacci
```

Add items from a file

```bash
Add the contents of ~/Documents/code-snippets/fibonacci.py to pocket pick with tags: python, algorithm, fibonacci
```

### Listing Items
List all items or tags:

```
list all my pocket picks
```

### Finding Items

Search for items in your knowledge base with tags

```
List pocket pick items with python and mcp tags
```

Search for text with specific content

```
pocket pick find "python"
```

### Get or Remove Items

Get or remove specific items:

```
get the pocket pick item with ID 1234-5678-90ab-cdef
remove the pocket pick item with ID 1234-5678-90ab-cdef
```

### Export to File

Export a pocket pick item's content to a file by its ID. This allows you to save code snippets directly to files, create executable scripts from stored knowledge, or share content with others:

```
export the pocket pick item with ID 1234-5678-90ab-cdef to /Users/username/Documents/exported-snippet.py
```

The tool requires an absolute file path and will automatically create any necessary parent directories if they don't exist.

### Backup

```
backup the pocket pick database to ~/Documents/pocket-pick-backup.db
```

## Themes Fabric Integration

Pocket Pick includes integration with the Themes Fabric pattern system, allowing you to:

- Import pattern descriptions and extracts into your knowledge base
- Get AI-suggested tags for your patterns
- Access your patterns directly through Claude conversations

For details on using the Themes Fabric integration, see the [Themes Fabric Integration Guide](./ai_docs/themes_fabric_integration.md).

## Search Modes

Pocket Pick supports various search modes:

- **substr**: (Default) Simple substring matching
- **fts**: Full-text search with powerful capabilities:
  - Regular word search: Matches all words in any order (e.g., "python programming" finds entries with both words)
  - Exact phrase search: Use quotes for exact phrase matching (e.g., `"python programming"` only finds entries with that exact phrase)
- **glob**: SQLite glob pattern matching (e.g., "test*" matches entries starting with "test")
- **regex**: Regular expression matching
- **exact**: Exact string matching

Example find commands:

```
Find items containing "pyt" using substring matching
Find items containing "def fibonacci" using full text search
Find items containing "test*" using glob pattern matching
Find items containing "^start.*test.*$" using regular expression matching
Find items containing "match exactly test" using exact string matching
```

## Database Structure

Pocket Pick uses a simple SQLite database with the following schema:

```sql
CREATE TABLE POCKET_PICK (
    id TEXT PRIMARY KEY,        -- UUID identifier
    created TIMESTAMP NOT NULL, -- Creation timestamp
    text TEXT NOT NULL,         -- Item content
    tags TEXT NOT NULL          -- JSON array of tags
)
```

The database file is located at `~/.pocket_pick.db` by default.

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v
```

### Running the Server Directly

```bash
# Start the MCP server
uv run mcp-server-pocket-pick

# With verbose logging
uv run mcp-server-pocket-pick -v

# With custom database location
uv run mcp-server-pocket-pick --database ./database.db
```

## Other Useful MCP Servers

### Fetch

```bash
claude mcp add http-fetch -- uvx mcp-server-fetch
```

---

Built with ❤️ by [IndyDevDan](https://www.youtube.com/@indydevdan) with [Claude Code](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview), and [Principled AI Coding](https://agenticengineer.com/principled-ai-coding)

