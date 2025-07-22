# Pocket Pick (MCP Server)
> See how we used AI Coding, Claude Code, and MCP to build this tool on the [@IndyDevDan youtube channel](https://youtu.be/d-SyGA0Avtw).

As engineers we end up reusing ideas, patterns and code snippets all the time but keeping track of these snippets can be hard and remembering where you stored them can be even harder. What if the exact snippet or idea you were looking for was one prompt away?

With Anthropic's new MCP (Model Context Protocol) and a minimal portable database layer - we can solve this problem. Pocket Pick is your personal engineering knowledge base that lets you quickly store ideas, patterns and code snippets and gives you a DEAD SIMPLE text or tag based searching to quickly find them in the future.

<img src="./images/pocket-pick.png" alt="Pocket Pick" style="max-width: 600px;">

## Features

- **Personal Knowledge Base**: Store code snippets, information, and ideas
- **Tag-Based Organization**: Add tags to categorize and filter your knowledge
- **Advanced Search Capabilities**: Multiple search modes including:
  - Traditional text search (substring, full-text, glob, regex, exact)
  - **Vector Similarity Search**: Semantic search using embeddings
  - **Hybrid Search**: Combines text, vector, and fuzzy matching for optimal results
- **Vector Embeddings**: Powered by `all-MiniLM-L6-v2` model (384-dimensional embeddings)
- **Performance Optimizations**:
  - Connection pooling for database efficiency
  - Multi-layer caching system for search results and embeddings
  - Asynchronous processing capabilities
- **MCP Integration**: Seamlessly works with Claude and other MCP-compatible AI assistants
- **SQLite Backend**: Fast, reliable, and portable database storage with FTS5 support
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
    "args": ["run", "pocket-pick-server"]
}
```

Custom Database for Claude Code

```json
{
    "command": "uv",
    "args": ["run", "pocket-pick-server", "--database", "./database.db"]
}
```

## Usage with Claude Code

```bash
# Add the pocket-pick server to Claude Code (if you're in the directory)
claude mcp add pocket-pick -- uv run pocket-pick-server

# Add the pocket-pick server to Claude Code with absolute path
claude mcp add pocket-pick -- uv --directory /path/to/pocket-pick-codebase run pocket-pick-server

# With custom database location
claude mcp add pocket-pick -- uv run pocket-pick-server --database ./database.db

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
| `pocket_find`        | Find items by text and/or tags with multiple search modes |
| `pocket_list`        | List all items, optionally filtered by tags  |
| `pocket_list_tags`   | List all tags with their counts              |
| `pocket_remove`      | Remove an item by ID                         |
| `pocket_get`         | Get a specific item by ID                    |
| `pocket_backup`      | Backup the database                          |
| `pocket_to_file_by_id` | Write an item's content to a file by its ID (requires absolute path) |
| `pocket_import_patterns` | Import Themes Fabric patterns from descriptions and extracts JSON files |
| `pocket_import_patterns_with_bodies` | Import Themes Fabric patterns with full pattern bodies from system.md files |
| `pocket_suggest_pattern_tags` | Use AI to suggest relevant tags for a Themes Fabric pattern file |
| `pocket_pattern_search` | Search for patterns by slug, title, or content |
| `pocket_get_pattern` | Get a pattern by slug (with fuzzy matching fallback) |
| `pocket_generate_embeddings` | Generate vector embeddings for all items in the database |
| `pocket_clear_cache` | Clear various caches (embeddings, search results, pattern index) |
| `pocket_cache_stats` | Get statistics about cache usage and performance |

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

Pocket Pick supports various search modes for different use cases:

### Traditional Search Modes
- **substr**: (Default) Simple substring matching
- **fts**: Full-text search with SQLite FTS5 capabilities:
  - Regular word search: Matches all words in any order (e.g., "python programming" finds entries with both words)
  - Exact phrase search: Use quotes for exact phrase matching (e.g., `"python programming"` only finds entries with that exact phrase)
- **glob**: SQLite glob pattern matching (e.g., "test*" matches entries starting with "test")
- **regex**: Regular expression matching
- **exact**: Exact string matching

### Advanced Search Modes
- **vector**: Pure semantic similarity search using vector embeddings
  - Finds content with similar meaning, even without exact word matches
  - Powered by the `all-MiniLM-L6-v2` sentence transformer model
- **hybrid**: **Intelligent combined search** (recommended for best results)
  - Combines vector similarity, full-text search, and fuzzy matching
  - Automatically weights and ranks results from multiple search methods
  - Provides the most comprehensive and relevant search results

### Search Mode Examples

```bash
# Traditional searches
Find items containing "pyt" using substring matching
Find items containing "def fibonacci" using full text search
Find items containing "test*" using glob pattern matching
Find items containing "^start.*test.*$" using regular expression matching
Find items containing "match exactly test" using exact string matching

# Advanced semantic searches
Find items about "async patterns" using vector search
Find items about "performance optimization" using hybrid search
Find items about "machine learning concepts" using vector search
```

## Database Structure

Pocket Pick uses an enhanced SQLite database with vector embedding support:

```sql
CREATE TABLE POCKET_PICK (
    id TEXT PRIMARY KEY,                              -- UUID identifier
    created TIMESTAMP NOT NULL,                       -- Creation timestamp
    text TEXT NOT NULL,                               -- Item content
    tags TEXT NOT NULL,                               -- JSON array of tags
    embedding BLOB,                                   -- Vector embedding data
    embedding_model TEXT DEFAULT 'all-MiniLM-L6-v2', -- Embedding model used
    embedding_updated TIMESTAMP                       -- Last embedding update
);

-- FTS5 virtual table for full-text search
CREATE VIRTUAL TABLE pocket_pick_fts USING fts5(
    text,
    content='POCKET_PICK',
    content_rowid='rowid'
);
```

### Database Features
- **Automatic Schema Migration**: Existing databases are automatically upgraded to support new features
- **FTS5 Full-Text Search**: Provides advanced text search capabilities
- **Vector Embedding Storage**: Stores 384-dimensional embeddings for semantic search
- **Performance Optimizations**: 
  - WAL journaling mode for better concurrency
  - Connection pooling for efficiency
  - Comprehensive indexing for fast queries

The database file is located at `~/.pocket_pick.db` by default.

## Advanced Features

### Vector Embeddings
Pocket Pick automatically generates vector embeddings for all stored content using the `all-MiniLM-L6-v2` model. These embeddings enable:
- Semantic similarity search that finds related content even without exact keyword matches
- Hybrid search that combines multiple search strategies for optimal results
- Intelligent content clustering and organization

### Caching System
The tool includes a multi-layer caching system for optimal performance:
- **Embedding Cache**: Stores generated embeddings to avoid recomputation
- **Search Result Cache**: Caches frequent search queries for faster responses
- **Pattern Index Cache**: Optimizes Themes Fabric pattern lookups

### Performance Optimizations
- **Connection Pooling**: Efficient database connection management
- **Asynchronous Processing**: Non-blocking operations for better responsiveness
- **Batch Processing**: Optimized embedding generation for multiple items
- **Thread-Safe Operations**: Proper handling of concurrent database access

### Troubleshooting

#### Database Migration Issues
If you encounter schema migration errors, the database will automatically upgrade to support new features. This includes:
- Adding embedding columns for vector search
- Creating FTS5 virtual tables for full-text search
- Setting up proper indexing for performance

#### Thread Safety
The tool includes proper SQLite thread safety handling with `check_same_thread=False` to support concurrent operations from MCP clients.

#### Cache Management
Use the cache management tools to optimize performance:
```bash
# Generate embeddings for all items
pocket_generate_embeddings

# Clear all caches
pocket_clear_cache

# View cache statistics
pocket_cache_stats
```

## Development

### Environment Setup

This project requires Python 3.10+ and uses UV for dependency management:

```bash
# Install UV if you don't have it
# See https://docs.astral.sh/uv/getting-started/installation/ for installation instructions

# Create and activate a virtual environment (optional but recommended)
python -m venv .venv
source .venv/bin/activate  # On Linux/Mac
# or
.\.venv\Scripts\activate  # On Windows

# Install dependencies using UV
uv sync
```

### Running Tests

**Important:** Always run tests using the Python interpreter from the UV environment to ensure compatibility with Python 3.10+ features.

```bash
# Run all tests
.venv/bin/python -m pytest

# Run with verbose output
.venv/bin/python -m pytest -v

# Run specific test file
.venv/bin/python -m pytest src/mcp_server_pocket_pick/tests/functionality/test_fabric_integration.py
```

### Running the Server Directly

Always use the UV environment when running the server:

```bash
# Start the MCP server
uv run pocket-pick-server

# With verbose logging
uv run pocket-pick-server -v

# With custom database location
uv run pocket-pick-server --database ./database.db
```

## Other Useful MCP Servers

### Fetch

```bash
claude mcp add http-fetch -- uvx mcp-server-fetch
```

---

Built with ❤️ by [IndyDevDan](https://www.youtube.com/@indydevdan) with [Claude Code](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview), and [Principled AI Coding](https://agenticengineer.com/principled-ai-coding)

