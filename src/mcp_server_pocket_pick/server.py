import logging
from pathlib import Path
from typing import List
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    TextContent,
    Tool,
)
from enum import Enum
from pydantic import BaseModel

from .modules.data_types import (
    AddCommand,
    AddFileCommand,
    FindCommand, 
    ListCommand,
    ListTagsCommand,
    RemoveCommand,
    GetCommand,
    BackupCommand,
    ToFileByIdCommand,
    ImportPatternsCommand,
    ImportPatternsWithBodiesCommand,
    SuggestPatternTagsCommand,
    PatternSearchCommand,
    GetPatternCommand,
)
from .modules.functionality.add import add
from .modules.functionality.add_file import add_file
from .modules.functionality.find import find
from .modules.functionality.list import list_items
from .modules.functionality.list_tags import list_tags
from .modules.functionality.remove import remove
from .modules.functionality.get import get
from .modules.functionality.backup import backup
from .modules.functionality.to_file_by_id import to_file_by_id
from .modules.functionality.import_patterns import import_patterns
from .modules.functionality.import_patterns_with_bodies import import_patterns_with_bodies
from .modules.functionality.suggest_pattern_tags import suggest_pattern_tags
from .modules.functionality.search_patterns import search_patterns, get_pattern
from .modules.constants import DEFAULT_SQLITE_DATABASE_PATH

logger = logging.getLogger(__name__)

class PocketAdd(BaseModel):
    text: str
    tags: List[str] = []
    db: str = str(DEFAULT_SQLITE_DATABASE_PATH)

class PocketAddFile(BaseModel):
    file_path: str
    tags: List[str] = []
    db: str = str(DEFAULT_SQLITE_DATABASE_PATH)

class PocketFind(BaseModel):
    text: str
    mode: str = "hybrid"  # Changed default to hybrid for better search results
    limit: int = 5
    info: bool = False
    tags: List[str] = []
    db: str = str(DEFAULT_SQLITE_DATABASE_PATH)

class PocketList(BaseModel):
    tags: List[str] = []
    limit: int = 100
    db: str = str(DEFAULT_SQLITE_DATABASE_PATH)

class PocketListTags(BaseModel):
    limit: int = 1000
    db: str = str(DEFAULT_SQLITE_DATABASE_PATH)

class PocketRemove(BaseModel):
    id: str
    db: str = str(DEFAULT_SQLITE_DATABASE_PATH)

class PocketGet(BaseModel):
    id: str
    db: str = str(DEFAULT_SQLITE_DATABASE_PATH)

class PocketBackup(BaseModel):
    backup_path: str
    db: str = str(DEFAULT_SQLITE_DATABASE_PATH)

class PocketToFileById(BaseModel):
    id: str
    output_file_path_abs: str
    db: str = str(DEFAULT_SQLITE_DATABASE_PATH)

class PocketImportPatterns(BaseModel):
    descriptions_path: str
    extracts_path: str
    db: str = str(DEFAULT_SQLITE_DATABASE_PATH)

class PocketImportPatternsWithBodies(BaseModel):
    patterns_root: str
    descriptions_path: str
    extracts_path: str
    db: str = str(DEFAULT_SQLITE_DATABASE_PATH)

class PocketSuggestPatternTags(BaseModel):
    pattern_path: str
    num_tags: int = 10
    existing_tags: List[str] = []
    db: str = str(DEFAULT_SQLITE_DATABASE_PATH)

class PocketPatternSearch(BaseModel):
    query: str
    patterns_path: str = "./patterns"
    limit: int = 5
    fuzzy: bool = True
    db: str = str(DEFAULT_SQLITE_DATABASE_PATH)

class PocketGetPattern(BaseModel):
    slug: str
    patterns_path: str = "./patterns"
    fuzzy: bool = True
    db: str = str(DEFAULT_SQLITE_DATABASE_PATH)

class PocketGenerateEmbeddings(BaseModel):
    batch_size: int = 32
    force_regenerate: bool = False
    db: str = str(DEFAULT_SQLITE_DATABASE_PATH)

class PocketClearCache(BaseModel):
    cache_type: str = "all"  # all, embeddings, search_results, pattern_index
    
class PocketCacheStats(BaseModel):
    detailed: bool = False

class PocketTools(str, Enum):
    ADD = "pocket_add"
    ADD_FILE = "pocket_add_file"
    FIND = "pocket_find"
    LIST = "pocket_list"
    LIST_TAGS = "pocket_list_tags"
    REMOVE = "pocket_remove"
    GET = "pocket_get"
    BACKUP = "pocket_backup"
    TO_FILE_BY_ID = "pocket_to_file_by_id"
    IMPORT_PATTERNS = "pocket_import_patterns"
    IMPORT_PATTERNS_WITH_BODIES = "pocket_import_patterns_with_bodies"
    SUGGEST_PATTERN_TAGS = "pocket_suggest_pattern_tags"
    PATTERN_SEARCH = "pocket_pattern_search"
    GET_PATTERN = "pocket_get_pattern"
    GENERATE_EMBEDDINGS = "pocket_generate_embeddings"
    CLEAR_CACHE = "pocket_clear_cache"
    CACHE_STATS = "pocket_cache_stats"

async def serve(sqlite_database: Path | None = None) -> None:
    logger.info(f"Starting Pocket Pick MCP server")
    
    # Determine which database path to use
    db_path = sqlite_database if sqlite_database is not None else DEFAULT_SQLITE_DATABASE_PATH
    logger.info(f"Using database at {db_path}")
    
    # Initialize the database at startup to ensure it exists
    from .modules.init_db import init_db
    connection = init_db(db_path)
    connection.close()
    logger.info(f"Database initialized at {db_path}")
    
    server = Server("pocket-pick")
    
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name=PocketTools.ADD,
                description="Add a new item to your pocket pick database",
                inputSchema=PocketAdd.schema(),
            ),
            Tool(
                name=PocketTools.ADD_FILE,
                description="Add a new item to your pocket pick database from a file",
                inputSchema=PocketAddFile.schema(),
            ),
            Tool(
                name=PocketTools.FIND,
                description="Find items in your pocket pick database by text and tags",
                inputSchema=PocketFind.schema(),
            ),
            Tool(
                name=PocketTools.LIST,
                description="List items in your pocket pick database, optionally filtered by tags",
                inputSchema=PocketList.schema(),
            ),
            Tool(
                name=PocketTools.LIST_TAGS,
                description="List all tags in your pocket pick database with their counts",
                inputSchema=PocketListTags.schema(),
            ),
            Tool(
                name=PocketTools.REMOVE,
                description="Remove an item from your pocket pick database by ID",
                inputSchema=PocketRemove.schema(),
            ),
            Tool(
                name=PocketTools.GET,
                description="Get an item from your pocket pick database by ID",
                inputSchema=PocketGet.schema(),
            ),
            Tool(
                name=PocketTools.BACKUP,
                description="Backup your pocket pick database to a specified location",
                inputSchema=PocketBackup.schema(),
            ),
            Tool(
                name=PocketTools.TO_FILE_BY_ID,
                description="Write a pocket pick item's content to a file by its ID (requires absolute file path)",
                inputSchema=PocketToFileById.schema(),
            ),
            Tool(
                name=PocketTools.IMPORT_PATTERNS,
                description="Import Themes Fabric patterns from descriptions and extracts JSON files",
                inputSchema=PocketImportPatterns.schema(),
            ),
            Tool(
                name=PocketTools.IMPORT_PATTERNS_WITH_BODIES,
                description="Import Themes Fabric patterns with full pattern bodies from the patterns directory",
                inputSchema=PocketImportPatternsWithBodies.schema(),
            ),
            Tool(
                name=PocketTools.SUGGEST_PATTERN_TAGS,
                description="Use AI to suggest relevant tags for a Themes Fabric pattern file",
                inputSchema=PocketSuggestPatternTags.schema(),
            ),
            Tool(
                name=PocketTools.PATTERN_SEARCH,
                description="Search for patterns by slug, title, or content",
                inputSchema=PocketPatternSearch.schema(),
            ),
            Tool(
                name=PocketTools.GET_PATTERN,
                description="Get a pattern by slug (with fuzzy matching fallback)",
                inputSchema=PocketGetPattern.schema(),
            ),
            Tool(
                name=PocketTools.GENERATE_EMBEDDINGS,
                description="Generate embeddings for all items in the database",
                inputSchema=PocketGenerateEmbeddings.schema(),
            ),
            Tool(
                name=PocketTools.CLEAR_CACHE,
                description="Clear various caches (embeddings, search results, pattern index)",
                inputSchema=PocketClearCache.schema(),
            ),
            Tool(
                name=PocketTools.CACHE_STATS,
                description="Get statistics about cache usage and performance",
                inputSchema=PocketCacheStats.schema(),
            ),
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        # Override db_path if provided via command line
        if sqlite_database is not None:
            arguments["db"] = str(sqlite_database)
        elif "db" not in arguments:
            # Use default if not specified
            arguments["db"] = str(DEFAULT_SQLITE_DATABASE_PATH)
        
        db_path = Path(arguments["db"])
        
        # Ensure the database exists and is initialized for every command
        from .modules.init_db import init_db
        connection = init_db(db_path)
        connection.close()
        
        match name:
            case PocketTools.ADD:
                command = AddCommand(
                    text=arguments["text"],
                    tags=arguments.get("tags", []),
                    db_path=db_path
                )
                result = add(command)
                return [TextContent(
                    type="text",
                    text=f"Added item with ID: {result.id}\nText: {result.text}\nTags: {', '.join(result.tags)}"
                )]
            
            case PocketTools.ADD_FILE:
                command = AddFileCommand(
                    file_path=arguments["file_path"],
                    tags=arguments.get("tags", []),
                    db_path=db_path
                )
                result = add_file(command)
                return [TextContent(
                    type="text",
                    text=f"Added file content with ID: {result.id}\nFrom file: {arguments['file_path']}\nTags: {', '.join(result.tags)}"
                )]
            
            case PocketTools.FIND:
                command = FindCommand(
                    text=arguments["text"],
                    mode=arguments.get("mode", "substr"),
                    limit=arguments.get("limit", 5),
                    info=arguments.get("info", False),
                    tags=arguments.get("tags", []),
                    db_path=db_path
                )
                results = find(command)
                
                if not results:
                    return [TextContent(
                        type="text",
                        text="No items found matching your search criteria."
                    )]
                
                output = []
                for item in results:
                    if command.info:
                        output.append(f"ID: {item.id}")
                        output.append(f"Created: {item.created.isoformat()}")
                        output.append(f"Tags: {', '.join(item.tags)}")
                        output.append(f"Text: {item.text}")
                        output.append("")
                    else:
                        output.append(item.text)
                        output.append("")
                
                return [TextContent(
                    type="text",
                    text="\n".join(output).strip()
                )]
            
            case PocketTools.LIST:
                command = ListCommand(
                    tags=arguments.get("tags", []),
                    limit=arguments.get("limit", 100),
                    db_path=db_path
                )
                results = list_items(command)
                
                if not results:
                    return [TextContent(
                        type="text",
                        text="No items found."
                    )]
                
                output = []
                for item in results:
                    output.append(f"ID: {item.id}")
                    output.append(f"Created: {item.created.isoformat()}")
                    output.append(f"Tags: {', '.join(item.tags)}")
                    output.append(f"Text: {item.text}")
                    output.append("")
                
                return [TextContent(
                    type="text",
                    text="\n".join(output).strip()
                )]
            
            case PocketTools.LIST_TAGS:
                command = ListTagsCommand(
                    limit=arguments.get("limit", 1000),
                    db_path=db_path
                )
                results = list_tags(command)
                
                if not results:
                    return [TextContent(
                        type="text",
                        text="No tags found."
                    )]
                
                output = ["Tags:"]
                for item in results:
                    output.append(f"{item['tag']} ({item['count']})")
                
                return [TextContent(
                    type="text",
                    text="\n".join(output)
                )]
            
            case PocketTools.REMOVE:
                command = RemoveCommand(
                    id=arguments["id"],
                    db_path=db_path
                )
                result = remove(command)
                
                if result:
                    return [TextContent(
                        type="text",
                        text=f"Item {command.id} removed successfully."
                    )]
                else:
                    return [TextContent(
                        type="text",
                        text=f"Item {command.id} not found."
                    )]
            
            case PocketTools.GET:
                command = GetCommand(
                    id=arguments["id"],
                    db_path=db_path
                )
                result = get(command)
                
                if result:
                    return [TextContent(
                        type="text",
                        text=f"ID: {result.id}\nCreated: {result.created.isoformat()}\nTags: {', '.join(result.tags)}\nText: {result.text}"
                    )]
                else:
                    return [TextContent(
                        type="text",
                        text=f"Item {command.id} not found."
                    )]
            
            case PocketTools.BACKUP:
                command = BackupCommand(
                    backup_path=Path(arguments["backup_path"]),
                    db_path=db_path
                )
                result = backup(command)
                
                if result:
                    return [TextContent(
                        type="text",
                        text=f"Database backed up successfully to {command.backup_path}"
                    )]
                else:
                    return [TextContent(
                        type="text",
                        text=f"Failed to backup database to {command.backup_path}"
                    )]
            
            case PocketTools.TO_FILE_BY_ID:
                command = ToFileByIdCommand(
                    id=arguments["id"],
                    output_file_path_abs=Path(arguments["output_file_path_abs"]),
                    db_path=db_path
                )
                result = to_file_by_id(command)
                
                if result:
                    return [TextContent(
                        type="text",
                        text=f"Content written successfully to {command.output_file_path_abs}"
                    )]
                else:
                    return [TextContent(
                        type="text",
                        text=f"Failed to write content to {command.output_file_path_abs}"
                    )]
            
            case PocketTools.IMPORT_PATTERNS:
                command = ImportPatternsCommand(
                    descriptions_path=Path(arguments["descriptions_path"]),
                    extracts_path=Path(arguments["extracts_path"]),
                    db_path=db_path
                )
                results = import_patterns(command)
                
                if results:
                    return [TextContent(
                        type="text",
                        text=f"Successfully imported {len(results)} patterns into your pocket pick database.\nFirst few patterns: {', '.join([item.tags[0] for item in results[:5]])}"
                    )]
                else:
                    return [TextContent(
                        type="text",
                        text=f"No patterns were imported. Please check your file paths and try again."
                    )]
            
            case PocketTools.IMPORT_PATTERNS_WITH_BODIES:
                command = ImportPatternsWithBodiesCommand(
                    patterns_root=Path(arguments["patterns_root"]),
                    descriptions_path=Path(arguments["descriptions_path"]),
                    extracts_path=Path(arguments["extracts_path"]),
                    db_path=db_path
                )
                results = import_patterns_with_bodies(command)
                
                if results:
                    # Extract pattern names for display
                    pattern_names = []
                    for item in results[:3]:
                        first_line = item.text.split('\n')[0]
                        pattern_name = first_line.strip('# ')
                        pattern_names.append(pattern_name)
                        
                    return [TextContent(
                        type="text",
                        text=f"Successfully imported {len(results)} patterns with bodies into your pocket pick database.\nFirst few patterns: {', '.join(pattern_names)}"
                    )]
                else:
                    return [TextContent(
                        type="text",
                        text=f"No patterns were imported. Please check your file paths and try again."
                    )]
            
            case PocketTools.SUGGEST_PATTERN_TAGS:
                command = SuggestPatternTagsCommand(
                    pattern_path=Path(arguments["pattern_path"]),
                    num_tags=arguments.get("num_tags", 10),
                    existing_tags=arguments.get("existing_tags", []),
                    db_path=db_path
                )
                results = suggest_pattern_tags(command)
                
                if results:
                    return [TextContent(
                        type="text",
                        text=f"Suggested tags for {command.pattern_path.name}:\n\n{', '.join(results)}"
                    )]
                else:
                    return [TextContent(
                        type="text",
                        text=f"Could not generate tags for {command.pattern_path.name}. Try providing some existing tags or use a longer document."
                    )]
            
            case PocketTools.PATTERN_SEARCH:
                command = PatternSearchCommand(
                    query=arguments["query"],
                    patterns_path=Path(arguments.get("patterns_path", "./patterns")),
                    limit=arguments.get("limit", 5),
                    fuzzy=arguments.get("fuzzy", True)
                )
                results = search_patterns(command)
                
                if results:
                    # Format results
                    output = [f"Found {len(results)} patterns matching '{command.query}':\n"]
                    
                    for i, item in enumerate(results, 1):
                        # Format title and tags
                        title_line = f"{i}. {item.title}"
                        tags_line = f"   Tags: {', '.join(item.tags)}" if item.tags else "   No tags"
                        
                        # Format summary or first line of content
                        if item.summary:
                            summary = item.summary
                        else:
                            # Extract first non-empty line from content
                            content_lines = [line.strip() for line in item.content.split('\n') if line.strip()]
                            summary = content_lines[0] if content_lines else "No content"
                        
                        summary_line = f"   Summary: {summary[:100]}..." if len(summary) > 100 else f"   Summary: {summary}"
                        
                        # Add slug for reference
                        slug_line = f"   Slug: {item.slug}"
                        
                        # Add to output
                        output.extend([title_line, tags_line, summary_line, slug_line, ""])
                    
                    output.append(f"\nUse `pocket_get_pattern` with the slug to retrieve the full pattern content.")
                    
                    return [TextContent(
                        type="text",
                        text="\n".join(output)
                    )]
                else:
                    return [TextContent(
                        type="text",
                        text=f"No patterns found matching '{command.query}'"
                    )]
            
            case PocketTools.GET_PATTERN:
                command = GetPatternCommand(
                    slug=arguments["slug"],
                    patterns_path=Path(arguments.get("patterns_path", "./patterns")),
                    fuzzy=arguments.get("fuzzy", True)
                )
                result = get_pattern(command)
                
                if result:
                    # Format the pattern content for display
                    output = [f"# {result.title}"]
                    
                    if result.tags:
                        output.append(f"\nTags: {', '.join(result.tags)}")
                    
                    if result.summary:
                        output.append(f"\n## Summary\n{result.summary}")
                    
                    output.append(f"\n## Content\n{result.content}")
                    
                    return [TextContent(
                        type="text",
                        text="\n".join(output)
                    )]
                else:
                    # Try to get similar slugs for helpful error message
                    from .modules.functionality.index_patterns import get_similar_slugs
                    similar_slugs = get_similar_slugs(arguments["slug"], str(Path(arguments.get("patterns_path", "./patterns"))))
                    
                    if similar_slugs:
                        suggestions = ", ".join([f"`{slug}`" for slug in similar_slugs])
                        return [TextContent(
                            type="text",
                            text=f"Pattern with slug '{arguments['slug']}' not found.\n\nDid you mean one of these? {suggestions}"
                        )]
                    else:
                        return [TextContent(
                            type="text",
                            text=f"Pattern with slug '{arguments['slug']}' not found."
                        )]
            
            case PocketTools.GENERATE_EMBEDDINGS:
                from .modules.search_engine import HybridSearchEngine
                
                batch_size = arguments.get("batch_size", 32)
                force_regenerate = arguments.get("force_regenerate", False)
                
                try:
                    search_engine = HybridSearchEngine()
                    success = await search_engine.ensure_embeddings_exist(db_path, batch_size)
                    
                    if success:
                        return [TextContent(
                            type="text",
                            text=f"Successfully generated/updated embeddings for all items in the database (batch size: {batch_size})"
                        )]
                    else:
                        return [TextContent(
                            type="text",
                            text="Failed to generate embeddings. Check logs for details."
                        )]
                except Exception as e:
                    return [TextContent(
                        type="text",
                        text=f"Error generating embeddings: {str(e)}"
                    )]
            
            case PocketTools.CLEAR_CACHE:
                from .modules.cache_layer import get_cache_manager
                
                cache_type = arguments.get("cache_type", "all")
                cache_manager = get_cache_manager()
                
                try:
                    if cache_type == "all":
                        cache_manager.clear_all()
                        message = "All caches cleared"
                    elif cache_type == "embeddings":
                        cache_manager.embeddings.clear()
                        message = "Embedding cache cleared"
                    elif cache_type == "search_results":
                        cache_manager.search_results.clear()
                        message = "Search results cache cleared"
                    elif cache_type == "pattern_index":
                        cache_manager.pattern_index.clear()
                        message = "Pattern index cache cleared"
                    else:
                        return [TextContent(
                            type="text",
                            text=f"Unknown cache type: {cache_type}. Valid types: all, embeddings, search_results, pattern_index"
                        )]
                    
                    return [TextContent(
                        type="text",
                        text=message
                    )]
                except Exception as e:
                    return [TextContent(
                        type="text",
                        text=f"Error clearing cache: {str(e)}"
                    )]
            
            case PocketTools.CACHE_STATS:
                from .modules.cache_layer import get_cache_manager
                
                detailed = arguments.get("detailed", False)
                cache_manager = get_cache_manager()
                
                try:
                    stats = cache_manager.get_stats()
                    
                    if detailed:
                        import json
                        stats_json = json.dumps(stats, indent=2, default=str)
                        return [TextContent(
                            type="text",
                            text=f"Detailed Cache Statistics:\n```json\n{stats_json}\n```"
                        )]
                    else:
                        # Simple summary
                        summary_lines = [
                            "Cache Statistics Summary:",
                            f"- Embedding cache size: {stats.get('embeddings', {}).get('memory_cache', {}).get('size', 'N/A')}",
                            f"- Search results cache size: {stats.get('search_results', {}).get('size', 'N/A')}",
                            f"- Pattern index cache size: {stats.get('pattern_index', {}).get('size', 'N/A')}",
                            f"- Cache directory: {stats.get('cache_directory', 'N/A')}"
                        ]
                        
                        return [TextContent(
                            type="text",
                            text="\n".join(summary_lines)
                        )]
                except Exception as e:
                    return [TextContent(
                        type="text",
                        text=f"Error getting cache stats: {str(e)}"
                    )]
            
            case _:
                raise ValueError(f"Unknown tool: {name}")
    
    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)