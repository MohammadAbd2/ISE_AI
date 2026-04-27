"""
Semantic Code Search API Routes

Provides intelligent code search capabilities
"""

from fastapi import APIRouter, Query
from typing import Optional

from app.services.semantic_search import get_semantic_search

router = APIRouter(prefix="/api/search", tags=["semantic-search"])


@router.get("/code")
async def search_code(
    query: str = Query(..., description="Search query (function name, keyword, pattern)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
):
    """Search code semantically with context understanding."""
    search = get_semantic_search()
    result = search.search(query, limit=limit)
    return result


@router.post("/index")
async def index_codebase():
    """Index the codebase for semantic search."""
    search = get_semantic_search()
    files_indexed = search.index_project()
    return {
        "success": True,
        "files_indexed": files_indexed,
        "message": f"Indexed {files_indexed} files",
    }


@router.get("/stats")
async def get_search_stats():
    """Get search index statistics."""
    search = get_semantic_search()
    return {
        "success": True,
        "indexed": search._indexed,
        "total_elements": len(search.index),
        "languages": list(set(item["language"] for item in search.index if item["language"] != "unknown")),
    }
