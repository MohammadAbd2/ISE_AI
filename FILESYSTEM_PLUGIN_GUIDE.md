# FileSystem Plugin - Advanced File System Introspection for ISE AI

## Overview

The **FileSystem Plugin** is a production-grade extension for the ISE AI Assistant that provides real-time, accurate file system access with advanced analysis capabilities. Unlike generic AI responses, this plugin actually queries your file system and delivers precise, categorized information.

## Features

### 🎯 Core Capabilities

1. **Real File System Queries**
   - Direct access to actual file system state
   - Not based on training data or memory
   - Always returns current, accurate information

2. **Advanced File Counting**
   - Total file counts with recursive options
   - Categorization by file type (source code, tests, config, docs, etc.)
   - Extension-based statistics

3. **Intelligent File Listing**
   - Detailed metadata for each file (size, type, category, permissions)
   - MIME type detection
   - Text vs binary classification
   - File preview generation for text files

4. **Powerful Search**
   - Search by filename pattern
   - Search by extension
   - Recursive search across directories
   - Result limiting for performance

5. **File Content Reading**
   - Read text files with encoding handling
   - Line-range selection
   - Binary file detection (prevents errors)
   - Large file handling (no excessive memory use)

6. **Project Structure Analysis**
   - Complete project overview
   - Categorized file statistics
   - Extension distribution
   - Size metrics

7. **Smart Ignore Patterns**
   - Automatically ignores build artifacts, dependencies, caches
   - Patterns: `.git`, `__pycache__`, `node_modules`, `.venv`, etc.
   - Customizable ignore lists

8. **Performance Optimization**
   - Built-in result caching (5-second TTL)
   - Memory-efficient directory traversal
   - Batch operations for large projects
   - Cache management endpoints

## Installation

The plugin is already integrated into the ISE AI backend. No additional installation required.

### Verify Installation

```bash
# Check if plugin routes are loaded
curl http://localhost:8000/api/filesystem/health
```

Response:
```json
{
  "status": "ok",
  "plugin": "FileSystem",
  "root": "/path/to/project",
  "version": "1.0.0"
}
```

## API Endpoints

### Base URL: `/api/filesystem`

#### 1. Health Check
```
GET /api/filesystem/health
```
Returns plugin status and version.

#### 2. Count Files
```
GET /api/filesystem/count?folder=tests&recursive=true
```
**Query Parameters:**
- `folder` (optional): Folder path relative to root
- `recursive` (optional, default: false): Count recursively

**Response:**
```json
{
  "success": true,
  "folder": "tests",
  "recursive": true,
  "total_files": 42,
  "by_category": {
    "test": 38,
    "config": 2,
    "documentation": 2
  },
  "by_extension": {
    ".py": 40,
    ".json": 2
  }
}
```

#### 3. List Files
```
GET /api/filesystem/list?folder=src&limit=50&extensions=.py,.ts
```
**Query Parameters:**
- `folder` (optional): Folder to list
- `limit` (optional, default: 100): Max files to return (1-1000)
- `extensions` (optional): Comma-separated extensions to filter

**Response:**
```json
{
  "success": true,
  "folder": "src",
  "count": 5,
  "files": [
    {
      "path": "src/main.py",
      "name": "main.py",
      "size": 2048,
      "extension": ".py",
      "category": "source_code",
      "is_dir": false,
      "is_text": true,
      "is_hidden": false,
      "readable": true,
      "writable": true,
      "created": "2024-04-08T12:30:00",
      "modified": "2024-04-08T14:45:00",
      "mime_type": "text/x-python"
    }
  ]
}
```

#### 4. List Directories
```
GET /api/filesystem/directories?recursive=false&limit=20
```
**Query Parameters:**
- `folder` (optional): Starting folder
- `recursive` (optional, default: false): List recursively
- `limit` (optional, default: 100): Max directories

#### 5. Search Files
```
GET /api/filesystem/search?pattern=test&by_extension=false&limit=50
```
**Query Parameters:**
- `pattern` (required): Search pattern (filename or extension)
- `folder` (optional): Search within folder
- `by_extension` (optional, default: false): Search by extension
- `limit` (optional, default: 50): Max results

**Examples:**
```
# Search for files containing "test"
GET /api/filesystem/search?pattern=test

# Search for Python files
GET /api/filesystem/search?pattern=.py&by_extension=true

# Search in specific folder
GET /api/filesystem/search?pattern=config&folder=backend
```

#### 6. Get File Info
```
GET /api/filesystem/info/src/main.py
```
Returns detailed metadata and preview for a file.

#### 7. Read File
```
GET /api/filesystem/read/README.md?start_line=1&end_line=50
```
**Query Parameters:**
- `start_line` (optional): Start line (1-indexed)
- `end_line` (optional): End line (1-indexed)

#### 8. Project Structure
```
GET /api/filesystem/structure
```
Returns complete project analysis with statistics.

#### 9. Statistics
```
GET /api/filesystem/stats?folder=backend
```
Detailed statistics for a folder or entire project.

#### 10. Clear Cache
```
POST /api/filesystem/cache/clear
```
Clear all cached results for fresh queries.

## Usage in Chat

The plugin integrates seamlessly with the ISE AI chat interface. Ask natural questions:

### Examples

**"How many files are in the tests folder?"**
- Plugin returns: Total count, breakdown by file type, file extensions

**"List all Python files in src"**
- Plugin returns: Filtered list with metadata

**"Show me the structure of the project"**
- Plugin returns: Complete directory tree with statistics

**"What files were modified recently?"**
- Plugin returns: Files sorted by modification time

**"Find all config files"**
- Plugin returns: All JSON, YAML, TOML, etc. files

## File Categories

Files are automatically categorized for better organization:

| Category | Extensions | Examples |
|----------|------------|----------|
| SOURCE_CODE | `.py`, `.js`, `.ts`, `.java`, etc. | Python, JavaScript, TypeScript files |
| TEST | Files with "test" in path | `test_*.py`, `*.test.js`, `tests/` |
| CONFIG | `.json`, `.yaml`, `.toml`, `.ini` | Configuration files |
| BUILD | `.sh`, `.gradle`, `.bat` | Build scripts |
| DOCUMENTATION | `.md`, `.rst`, `.txt` | Documentation files |
| DATA | `.csv`, `.db`, `.sqlite`, `.parquet` | Data files |
| ASSET | `.jpg`, `.png`, `.mp3`, `.mp4` | Media files |
| ARCHIVE | `.zip`, `.tar`, `.gz`, `.rar` | Archive files |
| EXECUTABLE | `.exe`, `.bin`, `.app` | Executable files |
| UNKNOWN | Other | Uncategorized files |

## Ignore Patterns

The plugin automatically ignores common patterns to reduce noise:

- `.git`, `.gitignore`
- `__pycache__`, `.pytest_cache`
- `node_modules`
- `.venv`, `venv`
- `.env` (security)
- `.idea`, `.vscode`
- `dist`, `build`, `target`
- `.DS_Store`, `Thumbs.db`
- `.lock`, `package-lock.json`, `yarn.lock`
- And 10+ more patterns

## Performance Characteristics

| Operation | Speed | Notes |
|-----------|-------|-------|
| Count files (1K files) | ~50ms | Cached, very fast |
| List files (limit 100) | ~30ms | Cached, instant retrieval |
| Search (limit 50) | ~100ms | Pattern matching |
| Project structure | ~200ms | Full analysis |
| Read large file (10MB) | ~500ms | Streamed, not cached |

## Error Handling

All endpoints return detailed error messages:

```json
{
  "success": false,
  "error": "Path not found: /invalid/path"
}
```

Common error codes:
- File/folder not found
- Permission denied
- Invalid path format
- Binary file detection (when trying to read non-text)
- Encoding errors

## Security Features

1. **Path Validation**: All paths validated against root directory
2. **Ignore Sensitive Files**: `.env` and credentials automatically ignored
3. **No Execution**: File system plugin never executes code
4. **Read-Only**: Does not modify files
5. **Permission Checks**: Respects file permissions

## Comparison: Plugin vs Other AI Agents

| Feature | ISE AI Plugin | Other Agents |
|---------|--------------|-------------|
| Real File System Access | ✅ Yes | ❌ Usually no |
| Actual File Counts | ✅ Accurate | ❌ Estimated/wrong |
| File Categorization | ✅ 9 categories | ❌ Generic |
| Project Analysis | ✅ Complete | ❌ Partial/none |
| Binary Detection | ✅ Auto-detected | ❌ Often errors |
| Caching | ✅ 5s TTL | ❌ N/A |
| Search Capabilities | ✅ Pattern + extension | ❌ Limited |
| Content Preview | ✅ Auto-generated | ❌ N/A |
| Performance | ✅ ~30-50ms | ❌ N/A |

## Testing

Comprehensive test suite with 40+ test cases:

```bash
pytest backend/app/plugins/tests/test_filesystem_plugin.py -v
```

### Test Coverage

- ✅ Basic file operations
- ✅ File searching and filtering
- ✅ File metadata extraction
- ✅ File categorization accuracy
- ✅ Ignore patterns
- ✅ Project structure analysis
- ✅ Caching mechanisms
- ✅ Recursive operations
- ✅ Edge cases and error handling
- ✅ Binary file detection
- ✅ Text file detection
- ✅ Large file handling

## Debugging

Enable verbose logging:

```python
from app.plugins.filesystem.plugin import FileSystemPlugin

plugin = FileSystemPlugin()
result = plugin.list_files(folder="src")
print(f"Cache hit: {'src' in plugin.cache}")
print(f"Result: {result}")
```

## Future Enhancements

Planned features for future releases:

1. **File Watching**: Real-time file change notifications
2. **Diff Tool**: Compare files and directories
3. **Batch Operations**: Move, copy, delete files
4. **Compression**: Create archives programmatically
5. **Backup**: Automated backup creation
6. **Smart Indexing**: Full-text search across files
7. **Git Integration**: Commit history and blame
8. **Statistics Trends**: Track file metrics over time

## Troubleshooting

### Plugin not loading?
Check `app.include_router` in `main.py` - ensure filesystem_routes are imported.

### Slow queries?
Check cache: `POST /api/filesystem/cache/clear` then retry

### Permission errors?
Ensure ISE AI process has read access to project directories

### Missing files?
Check ignore patterns - common directories like `.git` are excluded

## Support

For issues or feature requests, please check:
1. Plugin tests: `backend/app/plugins/tests/`
2. API routes: `backend/app/api/filesystem_routes.py`
3. Core plugin: `backend/app/plugins/filesystem/plugin.py`

## License

ISE AI FileSystem Plugin - Part of ISE AI Suite
