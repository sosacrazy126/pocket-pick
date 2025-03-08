# Pocket Pick

As engineers we end up reusing ideas, patterns and code snippets all the time but keeping track of these snippets can be hard and remembering where you stored them can be even harder. What if the exact snippet or idea you were looking for was one prompt away?

With Anthropics new MCP (model context protocol) and a minimal portable database layer - we can solve this problem. Pocket Pick is your personal engineering knowledge base that lets you quickly store ideas, patterns and code snippets and gives you a DEAD SIMPLE text or tag based searching to quickly find them in the future.

## Usage with Claude Code

Local Installation:

```
# Basic syntax
claude mcp add <name> <command> [args...]

# Example: Adding a local server
claude mcp add my-server -e API_KEY=123 -- /path/to/server arg1 arg2

# Add the pocket-pick server to claude code
claude mcp add pocket-pick \
    -- \
    uv --directory /Users/indydevdan/Documents/projects/pocket-pick \
    run mcp-server-pocket-pick

# List existing mcp servers
claude mcp list
```

## Extra Useful MCP Servers

### Fetch

```
claude mcp add http-fetch -- uvx mcp-server-fetch
```

