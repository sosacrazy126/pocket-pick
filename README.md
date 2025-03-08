# Pocket Pick

As engineers we end up reusing ideas, patterns and code snippets all the time but keeping track of these snippets can be hard and remembering where you stored them can be even harder. What if the exact snippet or idea you were looking for was one prompt away?

With Anthropic's new MCP (Model Context Protocol) and a minimal portable database layer - we can solve this problem. Pocket Pick is your personal engineering knowledge base that lets you quickly store ideas, patterns and code snippets and gives you a DEAD SIMPLE text or tag based searching to quickly find them in the future.

## Features

- **Personal Knowledge Base**: Store code snippets, information, and ideas
- **Tag-Based Organization**: Add tags to categorize and filter your knowledge
- **Flexible Search**: Find content using substring, full-text, glob, regex, or exact matching
- **MCP Integration**: Seamlessly works with Claude and other MCP-compatible AI assistants
- **SQLite Backend**: Fast, reliable, and portable database storage
- **Command-Line Interface**: Easy to use from the terminal

## Installation

```bash
# Clone the repository
git clone https://github.com/indydevdan/pocket-pick.git
cd pocket-pick

# Install with uv
uv install .
```

## Usage with Claude Code

```bash
# Basic syntax for adding MCP servers to Claude
claude mcp add <name> <command> [args...]

# Add the pocket-pick server to Claude Code
claude mcp add pocket-pick -- \
    uv --directory /path/to/pocket-pick \
    run mcp-server-pocket-pick

# With custom database location
claude mcp add pocket-pick -- \
    uv --directory /path/to/pocket-pick \
    run mcp-server-pocket-pick --database /path/to/my/database.db

# List existing MCP servers
claude mcp list
```

## MCP Tools

The following MCP tools are available in Pocket Pick:

| Tool | Description |
|------|-------------|
| `pocket_add` | Add a new item to your knowledge base |
| `pocket_find` | Find items by text and/or tags |
| `pocket_list` | List all items, optionally filtered by tags |
| `pocket_list_tags` | List all tags with their counts |
| `pocket_remove` | Remove an item by ID |
| `pocket_get` | Get a specific item by ID |
| `pocket_backup` | Backup the database |

## Using with Claude

After setting up Pocket Pick as an MCP server, you can use it with Claude in your conversations:

### Adding Items

```
Claude, please save this code snippet to my pocket pick:
```python
def fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a
```
with tags python, algorithm, fibonacci
```

### Finding Items

Search for items in your knowledge base:

```
Claude, can you find snippets about "fibonacci" in my pocket pick?
```

Search with specific tags:

```
Claude, show me all my snippets tagged with "python" and "algorithm"
```

### Managing Items

List all items or tags:

```
Claude, list all my pocket picks
Claude, what tags do I have in my pocket pick database?
```

Get or remove specific items:

```
Claude, show me the pocket pick item with ID 1234-5678-90ab-cdef
Claude, remove the pocket pick item with ID 1234-5678-90ab-cdef
```

### Backup

```
Claude, please backup my pocket pick database to ~/Documents/pocket-pick-backup.db
```

## Search Modes

Pocket Pick supports various search modes:

- **substr**: (Default) Simple substring matching
- **fts**: Full-text search that matches all words in the query
- **glob**: SQLite glob pattern matching (e.g., "test*" matches entries starting with "test")
- **regex**: Regular expression matching
- **exact**: Exact string matching

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
uv run mcp-server-pocket-pick --database /path/to/database.db
```

## Other Useful MCP Servers

### Fetch

```bash
claude mcp add http-fetch -- uvx mcp-server-fetch
```

---

Built with ❤️ using Claude

