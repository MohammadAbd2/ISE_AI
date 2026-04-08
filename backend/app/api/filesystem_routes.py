"""
API routes for FileSystem Plugin
Exposes file system capabilities through REST endpoints
"""
from fastapi import APIRouter, Query, HTTPException, Path as PathParam
from typing import Optional, List
from app.plugins.filesystem.plugin import FileSystemPlugin
import os

router = APIRouter(prefix="/api/filesystem", tags=["filesystem"])

# Initialize plugin with project root
plugin = FileSystemPlugin(os.getcwd())


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "plugin": "FileSystem",
        "root": str(plugin.root_path),
        "version": "1.0.0"
    }


@router.get("/count")
async def count_files(
    folder: Optional[str] = Query(None, description="Folder path relative to root"),
    recursive: bool = Query(False, description="Count recursively"),
):
    """Count files in a folder with categorization"""
    return plugin.count_files_in_folder(folder=folder, recursive=recursive)


@router.get("/list")
async def list_files(
    folder: Optional[str] = Query(None, description="Folder path relative to root"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum files to return"),
    extensions: Optional[str] = Query(None, description="Comma-separated extensions to filter (e.g., .py,.js)"),
):
    """List files in a folder"""
    ext_list = None
    if extensions:
        ext_list = [e.strip() for e in extensions.split(",")]
    return plugin.list_files(folder=folder, limit=limit, extensions=ext_list)


@router.get("/directories")
async def list_directories(
    folder: Optional[str] = Query(None, description="Folder path relative to root"),
    recursive: bool = Query(False, description="List recursively"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum directories to return"),
):
    """List directories with metadata"""
    return plugin.list_directories(folder=folder, recursive=recursive, limit=limit)


@router.get("/search")
async def search_files(
    pattern: str = Query(..., description="Search pattern (filename or extension)"),
    folder: Optional[str] = Query(None, description="Folder to search in"),
    by_extension: bool = Query(False, description="Search by extension instead of name"),
    limit: int = Query(50, ge=1, le=500, description="Maximum results"),
):
    """Search for files"""
    return plugin.search_files(
        pattern=pattern,
        folder=folder,
        by_extension=by_extension,
        limit=limit
    )


@router.get("/info/{file_path:path}")
async def get_file_info(file_path: str = PathParam(..., description="File path relative to root")):
    """Get detailed information about a file"""
    return plugin.get_file_info(file_path)


@router.get("/read/{file_path:path}")
async def read_file(
    file_path: str = PathParam(..., description="File path relative to root"),
    start_line: Optional[int] = Query(None, ge=1, description="Start line number (1-indexed)"),
    end_line: Optional[int] = Query(None, ge=1, description="End line number (1-indexed)"),
):
    """Read file content"""
    lines = None
    if start_line is not None and end_line is not None:
        lines = (start_line, end_line)
    return plugin.read_file(file_path, lines=lines)


@router.get("/structure")
async def get_project_structure():
    """Get complete project structure and statistics"""
    return plugin.get_project_structure()


@router.post("/cache/clear")
async def clear_cache():
    """Clear all caches"""
    return plugin.clear_cache()


@router.get("/stats")
async def get_statistics(
    folder: Optional[str] = Query(None, description="Folder to analyze"),
):
    """Get detailed statistics about files in a folder"""
    if folder:
        result = plugin.count_files_in_folder(folder=folder, recursive=True)
    else:
        result = plugin.get_project_structure()
    return result
