from pathlib import Path
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from .constants import DEFAULT_SQLITE_DATABASE_PATH


class AddCommand(BaseModel):
    text: str
    tags: List[str] = []
    db_path: Path = DEFAULT_SQLITE_DATABASE_PATH


class AddFileCommand(BaseModel):
    file_path: str
    tags: List[str] = []
    db_path: Path = DEFAULT_SQLITE_DATABASE_PATH


class FindCommand(BaseModel):
    text: str
    mode: str = "substr"  # substr | fts | glob | regex | exact
    limit: int = 5
    info: bool = False
    tags: List[str] = []
    db_path: Path = DEFAULT_SQLITE_DATABASE_PATH


class ListCommand(BaseModel):
    tags: List[str] = []
    limit: int = 100
    db_path: Path = DEFAULT_SQLITE_DATABASE_PATH


class ListTagsCommand(BaseModel):
    limit: int = 1000
    db_path: Path = DEFAULT_SQLITE_DATABASE_PATH


class RemoveCommand(BaseModel):
    id: str
    db_path: Path = DEFAULT_SQLITE_DATABASE_PATH


class GetCommand(BaseModel):
    id: str
    db_path: Path = DEFAULT_SQLITE_DATABASE_PATH


class GetPatternCommand(BaseModel):
    slug: str
    patterns_path: Path = Path("./patterns")
    fuzzy: bool = True


class BackupCommand(BaseModel):
    backup_path: Path
    db_path: Path = DEFAULT_SQLITE_DATABASE_PATH


class ToFileByIdCommand(BaseModel):
    id: str
    output_file_path_abs: Path
    db_path: Path = DEFAULT_SQLITE_DATABASE_PATH


class ImportPatternsCommand(BaseModel):
    descriptions_path: Path
    extracts_path: Path
    db_path: Path = DEFAULT_SQLITE_DATABASE_PATH


class ImportPatternsWithBodiesCommand(BaseModel):
    patterns_root: Path
    descriptions_path: Path
    extracts_path: Path
    db_path: Path = DEFAULT_SQLITE_DATABASE_PATH


class SuggestPatternTagsCommand(BaseModel):
    pattern_path: Path
    num_tags: int = 10
    existing_tags: List[str] = []
    db_path: Path = DEFAULT_SQLITE_DATABASE_PATH


class PatternSearchCommand(BaseModel):
    query: str
    patterns_path: Path = Path("./patterns")
    limit: int = 5
    fuzzy: bool = True


class PatternItem(BaseModel):
    slug: str
    title: str
    summary: Optional[str]
    tags: List[str]
    content: str
    score: float


class PocketItem(BaseModel):
    id: str
    created: datetime
    text: str
    tags: List[str]