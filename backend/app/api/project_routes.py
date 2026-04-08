"""
API routes for project analysis and file operations
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from app.services.project_analyzer import ProjectAnalyzer
from app.services.project_tools import ProjectTools

router = APIRouter(prefix="/api/project", tags=["project"])

# Initialize services
analyzer = ProjectAnalyzer()
tools = ProjectTools()

@router.get("/info")
async def get_project_info():
    """Get comprehensive project information"""
    return tools.get_project_info()

@router.get("/metadata")
async def get_project_metadata():
    """Get project metadata"""
    metadata = analyzer.get_project_metadata()
    return {
        'success': 'error' not in metadata,
        'data': metadata
    }

@router.get("/stats")
async def get_project_statistics():
    """Get project file statistics"""
    stats = analyzer.get_file_statistics()
    return {
        'success': True,
        'data': stats
    }

@router.get("/files")
async def list_files(
    folder: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=1000)
):
    """List files in project"""
    return tools.list_project_files(folder, limit)

@router.get("/folders")
async def list_folders(
    folder: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500)
):
    """List folders in project"""
    return tools.list_project_structure(folder, limit)

@router.get("/count-files")
async def count_files(folder: Optional[str] = Query(None)):
    """Count files in folder"""
    return tools.count_files(folder)

@router.get("/search")
async def search_files(
    pattern: str = Query(...),
    file_type: Optional[str] = Query(None)
):
    """Search for files matching pattern"""
    return tools.search_in_project(pattern, file_type)

@router.get("/read")
async def read_file(file_path: str = Query(...)):
    """Read file content"""
    return tools.read_file(file_path)

@router.get("/read-snippet")
async def read_file_snippet(
    file_path: str = Query(...),
    start_line: int = Query(1, ge=1),
    end_line: Optional[int] = Query(None)
):
    """Read specific lines from file"""
    return tools.read_file_snippet(file_path, start_line, end_line)

@router.post("/write")
async def write_file(
    file_path: str = Query(...),
    content: str = Query(...),
    create_if_missing: bool = Query(True)
):
    """Write content to file"""
    return tools.write_file(file_path, content, create_if_missing)

@router.post("/append")
async def append_to_file(
    file_path: str = Query(...),
    content: str = Query(...)
):
    """Append content to file"""
    return tools.append_to_file(file_path, content)

@router.post("/create")
async def create_file(
    file_path: str = Query(...),
    content: str = Query("")
):
    """Create a new file"""
    return tools.create_file(file_path, content)

@router.get("/search-content")
async def search_file_content(
    pattern: str = Query(...),
    file_types: Optional[List[str]] = Query(None)
):
    """Search for pattern in file contents"""
    return tools.search_file_content(pattern, file_types)
