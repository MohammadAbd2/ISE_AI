"""
FileSystem Plugin - Advanced file system introspection and analysis for ISE AI
Provides real-time file system queries with caching, pattern matching, and detailed analysis
"""
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime
import os
import fnmatch
import mimetypes
from enum import Enum
import json


class FileCategory(Enum):
    """File categorization"""
    SOURCE_CODE = "source_code"
    TEST = "test"
    CONFIG = "config"
    BUILD = "build"
    DOCUMENTATION = "documentation"
    DATA = "data"
    ASSET = "asset"
    ARCHIVE = "archive"
    EXECUTABLE = "executable"
    UNKNOWN = "unknown"


@dataclass
class FileMetadata:
    """Complete file metadata"""
    path: str
    name: str
    size: int
    extension: str
    category: FileCategory
    is_dir: bool
    is_symlink: bool
    is_hidden: bool
    created: float
    modified: float
    accessed: float
    readable: bool
    writable: bool
    is_text: bool
    mime_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "path": self.path,
            "name": self.name,
            "size": self.size,
            "extension": self.extension,
            "category": self.category.value,
            "is_dir": self.is_dir,
            "is_symlink": self.is_symlink,
            "is_hidden": self.is_hidden,
            "created": datetime.fromtimestamp(self.created).isoformat(),
            "modified": datetime.fromtimestamp(self.modified).isoformat(),
            "accessed": datetime.fromtimestamp(self.accessed).isoformat(),
            "readable": self.readable,
            "writable": self.writable,
            "is_text": self.is_text,
            "mime_type": self.mime_type,
        }


class FileSystemPlugin:
    """Advanced FileSystem Plugin for ISE AI"""

    # Ignore patterns for files/folders
    DEFAULT_IGNORE_PATTERNS = {
        ".git", ".gitignore", "__pycache__", ".pytest_cache", "node_modules",
        ".venv", "venv", ".env", ".idea", ".vscode", "dist", "build",
        "target", ".gradle", ".DS_Store", "Thumbs.db", ".lock",
        "package-lock.json", "yarn.lock", "pnpm-lock.yaml", ".next", "out",
        ".cache", ".pytest", ".tox", ".eggs", ".mypy_cache", ".egg-info",
        "*.pyc", "*.pyo", "*.class", "*.o", "*.so", ".coverage"
    }

    # File categorization patterns
    SOURCE_CODE_EXTENSIONS = {
        ".py", ".ts", ".tsx", ".js", ".jsx", ".java", ".kt", ".rs", ".go",
        ".cpp", ".cc", ".cxx", ".h", ".cs", ".rb", ".php", ".swift", ".m",
        ".scala", ".groovy", ".clj", ".ex", ".erl"
    }

    TEST_PATTERNS = {"test", "spec", "_test.py", ".test.js", ".spec.ts", "tests/"}

    CONFIG_EXTENSIONS = {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf"}

    BUILD_EXTENSIONS = {".sh", ".gradle", ".maven", ".make", ".bat", ".ps1"}

    DOCUMENTATION_EXTENSIONS = {".md", ".rst", ".txt", ".adoc", ".tex"}

    # Text file extensions
    TEXT_EXTENSIONS = {
        ".txt", ".md", ".rst", ".py", ".js", ".ts", ".java", ".cs", ".rb",
        ".go", ".rs", ".cpp", ".c", ".h", ".json", ".yaml", ".yml", ".xml",
        ".html", ".css", ".scss", ".less", ".sql", ".sh", ".bash", ".env"
    }

    def __init__(self, root_path: Optional[str] = None):
        """Initialize FileSystem Plugin"""
        self.root_path = Path(root_path or os.getcwd())
        self.cache: Dict[str, Any] = {}
        self.cache_timestamp: Dict[str, float] = {}
        self.cache_ttl = 5  # Cache time-to-live in seconds
        
        if not self.root_path.exists():
            raise ValueError(f"Root path does not exist: {self.root_path}")

    def _should_ignore(self, path: Path, ignore_patterns: Optional[Set[str]] = None) -> bool:
        """Check if path should be ignored"""
        if ignore_patterns is None:
            ignore_patterns = self.DEFAULT_IGNORE_PATTERNS

        # Check parts of the path
        for part in path.parts:
            if part in ignore_patterns or part.startswith("."):
                return True

        # Check against patterns with wildcards
        name = path.name
        for pattern in ignore_patterns:
            if fnmatch.fnmatch(name, pattern):
                return True

        return False

    def _categorize_file(self, path: Path) -> FileCategory:
        """Categorize a file"""
        name_lower = path.name.lower()
        ext = path.suffix.lower()

        # Check if test file
        if any(test_pattern in str(path).lower() for test_pattern in self.TEST_PATTERNS):
            return FileCategory.TEST

        # Check category by extension
        if ext in self.SOURCE_CODE_EXTENSIONS:
            return FileCategory.SOURCE_CODE
        elif ext in self.CONFIG_EXTENSIONS:
            return FileCategory.CONFIG
        elif ext in self.BUILD_EXTENSIONS:
            return FileCategory.BUILD
        elif ext in self.DOCUMENTATION_EXTENSIONS:
            return FileCategory.DOCUMENTATION
        elif ext in {".zip", ".tar", ".gz", ".rar", ".7z"}:
            return FileCategory.ARCHIVE
        elif ext in {".exe", ".bin", ".app", ".msi", ".deb", ".rpm"}:
            return FileCategory.EXECUTABLE
        elif ext in {".jpg", ".png", ".gif", ".svg", ".ico", ".webp", ".mp3", ".mp4", ".pdf"}:
            return FileCategory.ASSET
        elif ext in {".csv", ".db", ".sqlite", ".parquet", ".pkl"}:
            return FileCategory.DATA

        return FileCategory.UNKNOWN

    def _is_text_file(self, path: Path) -> bool:
        """Check if file is text-based"""
        ext = path.suffix.lower()
        if ext in self.TEXT_EXTENSIONS:
            return True
        
        # For unknown extensions, check if it's text
        if ext in {".bin", ".exe", ".so", ".o", ".pyc", ".class"}:
            return False

        # Try to read first bytes
        try:
            with open(path, "rb") as f:
                chunk = f.read(512)
                return self._is_text_content(chunk)
        except Exception:
            return False

    @staticmethod
    def _is_text_content(chunk: bytes) -> bool:
        """Check if content is text"""
        if not chunk:
            return True
        
        # Check for null bytes (strong indicator of binary)
        if b'\x00' in chunk:
            return False
        
        try:
            chunk.decode("utf-8")
            return True
        except UnicodeDecodeError:
            return False

    def _get_file_metadata(self, path: Path, relative_to: Optional[Path] = None) -> FileMetadata:
        """Get complete file metadata"""
        try:
            stat = path.stat()
            # Use resolved root_path for relative path calculation
            try:
                relative_path = str(path.relative_to(self.root_path.resolve()))
            except ValueError:
                # Fallback if not relative to root
                relative_path = str(path.relative_to(relative_to or self.root_path))
            
            mime_type, _ = mimetypes.guess_type(str(path))

            return FileMetadata(
                path=relative_path,
                name=path.name,
                size=stat.st_size,
                extension=path.suffix.lower(),
                category=self._categorize_file(path),
                is_dir=path.is_dir(),
                is_symlink=path.is_symlink(),
                is_hidden=path.name.startswith("."),
                created=stat.st_ctime,
                modified=stat.st_mtime,
                accessed=stat.st_atime,
                readable=os.access(path, os.R_OK),
                writable=os.access(path, os.W_OK),
                is_text=self._is_text_file(path) if path.is_file() else False,
                mime_type=mime_type,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to get metadata for {path}: {e}")

    def count_files_in_folder(self, folder: Optional[str] = None, recursive: bool = False) -> Dict[str, Any]:
        """Count files in a folder with categorization"""
        cache_key = f"count_files:{folder}:{recursive}"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]

        try:
            target_path = self._resolve_path(folder)
            file_count = 0
            category_counts: Dict[str, int] = {}
            extension_counts: Dict[str, int] = {}

            if recursive:
                iterator = target_path.rglob("*")
            else:
                iterator = target_path.glob("*")

            for item in iterator:
                if self._should_ignore(item):
                    continue

                if item.is_file():
                    file_count += 1
                    try:
                        metadata = self._get_file_metadata(item)
                        category = metadata.category.value
                        category_counts[category] = category_counts.get(category, 0) + 1

                        ext = metadata.extension or "no_extension"
                        extension_counts[ext] = extension_counts.get(ext, 0) + 1
                    except Exception:
                        pass

            result = {
                "success": True,
                "folder": folder or "root",
                "recursive": recursive,
                "total_files": file_count,
                "by_category": category_counts,
                "by_extension": extension_counts,
            }

            self._cache_result(cache_key, result)
            return result

        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_files(self, folder: Optional[str] = None, limit: int = 100, extensions: Optional[List[str]] = None) -> Dict[str, Any]:
        """List files in a folder with detailed metadata"""
        cache_key = f"list_files:{folder}:{limit}:{extensions}"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]

        try:
            target_path = self._resolve_path(folder)
            files = []

            for item in sorted(target_path.glob("*")):
                if self._should_ignore(item) or not item.is_file():
                    continue

                # Filter by extension if specified
                if extensions and item.suffix.lower() not in extensions:
                    continue

                try:
                    metadata = self._get_file_metadata(item)
                    files.append(metadata.to_dict())
                except Exception:
                    continue

                if len(files) >= limit:
                    break

            result = {
                "success": True,
                "folder": folder or "root",
                "count": len(files),
                "limit": limit,
                "files": files,
            }

            self._cache_result(cache_key, result)
            return result

        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_directories(self, folder: Optional[str] = None, recursive: bool = False, limit: int = 100) -> Dict[str, Any]:
        """List directories with metadata"""
        cache_key = f"list_dirs:{folder}:{recursive}:{limit}"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]

        try:
            target_path = self._resolve_path(folder)
            directories = []

            if recursive:
                iterator = target_path.rglob("*")
            else:
                iterator = target_path.glob("*")

            for item in sorted(iterator):
                if self._should_ignore(item):
                    continue

                if item.is_dir():
                    try:
                        file_count = len(list(item.glob("*")))
                        dir_count = len(list(item.glob("*/*")))
                        relative_path = str(item.relative_to(self.root_path))

                        directories.append({
                            "path": relative_path,
                            "name": item.name,
                            "file_count": file_count,
                            "subdir_count": dir_count,
                            "is_hidden": item.name.startswith("."),
                        })

                        if len(directories) >= limit:
                            break
                    except Exception:
                        continue

            result = {
                "success": True,
                "folder": folder or "root",
                "recursive": recursive,
                "count": len(directories),
                "directories": directories,
            }

            self._cache_result(cache_key, result)
            return result

        except Exception as e:
            return {"success": False, "error": str(e)}

    def search_files(self, pattern: str, folder: Optional[str] = None, by_extension: bool = False, limit: int = 50) -> Dict[str, Any]:
        """Search for files by name or extension"""
        cache_key = f"search_files:{pattern}:{folder}:{by_extension}:{limit}"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]

        try:
            target_path = self._resolve_path(folder)
            matches = []

            for item in target_path.rglob("*"):
                if self._should_ignore(item) or not item.is_file():
                    continue

                if by_extension:
                    if item.suffix.lower() == pattern.lower():
                        matches.append(self._get_file_metadata(item).to_dict())
                else:
                    if fnmatch.fnmatch(item.name.lower(), f"*{pattern.lower()}*"):
                        matches.append(self._get_file_metadata(item).to_dict())

                if len(matches) >= limit:
                    break

            result = {
                "success": True,
                "pattern": pattern,
                "by_extension": by_extension,
                "count": len(matches),
                "files": matches,
            }

            self._cache_result(cache_key, result)
            return result

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get detailed information about a specific file"""
        try:
            path = self._resolve_path(file_path)

            if not path.exists():
                return {"success": False, "error": f"File not found: {file_path}"}

            metadata = self._get_file_metadata(path)
            result = {
                "success": True,
                "file": metadata.to_dict(),
            }

            # Add content preview for text files
            if metadata.is_text and metadata.size < 100000:  # Only for files < 100KB
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        lines = content.split("\n")
                        result["preview"] = {
                            "lines_total": len(lines),
                            "first_50_lines": "\n".join(lines[:50]),
                        }
                except Exception:
                    pass

            return result

        except Exception as e:
            return {"success": False, "error": str(e)}

    def read_file(self, file_path: str, lines: Optional[Tuple[int, int]] = None) -> Dict[str, Any]:
        """Read file content with optional line range"""
        try:
            path = self._resolve_path(file_path)

            if not path.exists():
                return {"success": False, "error": f"File not found: {file_path}"}

            if not path.is_file():
                return {"success": False, "error": f"Path is not a file: {file_path}"}

            metadata = self._get_file_metadata(path)

            if not metadata.is_text:
                return {
                    "success": False,
                    "error": f"File is not text-based (detected as {metadata.mime_type})"
                }

            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            if lines:
                start, end = lines
                file_lines = content.split("\n")
                content = "\n".join(file_lines[start - 1:end])

            return {
                "success": True,
                "file": str(path.relative_to(self.root_path)),
                "size": metadata.size,
                "lines": len(content.split("\n")),
                "content": content,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_project_structure(self) -> Dict[str, Any]:
        """Get complete project structure summary"""
        cache_key = "project_structure"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]

        try:
            stats = {
                "total_files": 0,
                "total_dirs": 0,
                "by_category": {},
                "by_extension": {},
                "total_size": 0,
            }

            for item in self.root_path.rglob("*"):
                if self._should_ignore(item):
                    continue

                if item.is_file():
                    stats["total_files"] += 1
                    stats["total_size"] += item.stat().st_size

                    try:
                        metadata = self._get_file_metadata(item)
                        cat = metadata.category.value
                        stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1

                        ext = metadata.extension or "no_extension"
                        stats["by_extension"][ext] = stats["by_extension"].get(ext, 0) + 1
                    except Exception:
                        pass

                elif item.is_dir():
                    stats["total_dirs"] += 1

            result = {
                "success": True,
                "root": str(self.root_path),
                "stats": stats,
            }

            self._cache_result(cache_key, result)
            return result

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _resolve_path(self, path: Optional[str]) -> Path:
        """Resolve a path relative to root"""
        if not path:
            return self.root_path

        target = self.root_path / path
        try:
            return target.resolve()
        except Exception:
            return target

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache entry is valid"""
        if key not in self.cache:
            return False

        age = datetime.now().timestamp() - self.cache_timestamp.get(key, 0)
        return age < self.cache_ttl

    def _cache_result(self, key: str, result: Dict[str, Any]) -> None:
        """Cache a result"""
        self.cache[key] = result
        self.cache_timestamp[key] = datetime.now().timestamp()

    def clear_cache(self) -> Dict[str, Any]:
        """Clear all caches"""
        self.cache.clear()
        self.cache_timestamp.clear()
        return {"success": True, "message": "Cache cleared"}
