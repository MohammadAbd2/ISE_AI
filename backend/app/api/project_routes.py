"""
API routes for project analysis and file operations
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from app.services.project_analyzer import ProjectAnalyzer
from app.services.project_tools import ProjectTools
from app.services.codebase_map import get_codebase_map_service
from app.services.project_exports import get_project_export_service

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


@router.get("/map")
async def get_codebase_map():
    """Get a high-level architecture map of the codebase."""
    service = get_codebase_map_service()
    return {
        "success": True,
        "data": service.build_map(),
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


@router.post("/export")
async def export_project(session_id: str = Query("manual-export"), folder: Optional[str] = Query(None)):
    """Create a ZIP export for the project or a subfolder and register it as a downloadable artifact."""
    source_dir = analyzer.project_root if not folder else (analyzer.project_root / folder)
    if not source_dir.exists() or not source_dir.is_dir():
        raise HTTPException(status_code=404, detail="Project folder not found")
    exporter = get_project_export_service()
    result = await exporter.export_directory(
        source_dir=source_dir,
        session_id=session_id,
        title=f"{source_dir.name} export",
        filename=f"{source_dir.name}.zip",
    )
    return {
        "success": True,
        "artifact": result.artifact,
        "zip_path": str(result.zip_path),
        "file_count": result.file_count,
    }
