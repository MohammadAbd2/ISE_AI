"""
Project Indexing API Routes - Allow plugins to trigger project indexing
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.project_indexing import get_project_indexer, index_project


router = APIRouter()


class IndexProjectRequest(BaseModel):
    root_path: str
    project_name: str = ""


class IndexProjectResponse(BaseModel):
    success: bool
    message: str
    total_files: int = 0
    total_dirs: int = 0
    indexed_at: str = ""


@router.post("/api/project/index", response_model=IndexProjectResponse)
async def index_project_endpoint(payload: IndexProjectRequest):
    """
    Index a project for fast filesystem queries.
    Called by IDE plugins when a project is opened.
    """
    try:
        indexer = get_project_indexer()
        result = indexer.index_project(payload.root_path)
        
        return IndexProjectResponse(
            success=True,
            message=f"Successfully indexed project: {payload.project_name or payload.root_path}",
            total_files=result.total_files,
            total_dirs=result.total_dirs,
            indexed_at=result.indexed_at,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to index project: {str(e)}")


@router.get("/api/project/index/status")
async def get_project_index_status():
    """Get the current project index status"""
    indexer = get_project_indexer()
    
    if not indexer.current_index:
        return {
            "indexed": False,
            "message": "No project has been indexed yet",
        }
    
    return {
        "indexed": True,
        "root_path": indexer.current_index.root_path,
        "total_files": indexer.current_index.total_files,
        "total_dirs": indexer.current_index.total_dirs,
        "indexed_at": indexer.current_index.indexed_at,
        "is_indexing": indexer.is_indexing,
    }


@router.get("/api/project/index/structure")
async def get_project_structure():
    """Get the complete project structure summary"""
    indexer = get_project_indexer()
    
    if not indexer.current_index:
        raise HTTPException(status_code=404, detail="Project not indexed")
    
    return indexer.get_project_structure()
