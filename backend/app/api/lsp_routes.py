"""
LSP (Language Server Protocol) API Routes

Provides code intelligence features
"""

from fastapi import APIRouter, Query
from typing import Optional

from app.services.lsp_integration import get_lsp_integration

router = APIRouter(prefix="/api/lsp", tags=["lsp"])


@router.post("/index")
async def index_codebase():
    """Index codebase for LSP features."""
    lsp = get_lsp_integration()
    files_indexed = lsp.index_project()
    return {
        "success": True,
        "files_indexed": files_indexed,
        "message": f"Indexed {files_indexed} files",
    }


@router.get("/definition")
async def go_to_definition(
    file_path: str = Query(..., description="File path"),
    line: int = Query(..., description="Line number (1-indexed)"),
    column: int = Query(0, description="Column number"),
):
    """Find where a symbol is defined."""
    lsp = get_lsp_integration()
    return lsp.go_to_definition(file_path, line, column)


@router.get("/hover")
async def get_hover_info(
    file_path: str = Query(..., description="File path"),
    line: int = Query(..., description="Line number (1-indexed)"),
    column: int = Query(0, description="Column number"),
):
    """Get hover documentation."""
    lsp = get_lsp_integration()
    return lsp.get_hover_info(file_path, line, column)


@router.get("/diagnostics")
async def get_diagnostics(
    file_path: Optional[str] = Query(None, description="Filter by file"),
):
    """Get diagnostics (errors, warnings)."""
    lsp = get_lsp_integration()
    return lsp.get_diagnostics(file_path)


@router.get("/references")
async def find_references(
    symbol_name: str = Query(..., description="Symbol name"),
):
    """Find all references to a symbol."""
    lsp = get_lsp_integration()
    return lsp.find_references(symbol_name)


@router.get("/symbols")
async def search_symbols(
    query: str = Query(..., description="Search query"),
    kind: Optional[str] = Query(None, description="Symbol kind filter"),
):
    """Search for symbols by name."""
    lsp = get_lsp_integration()
    return lsp.search_symbols(query, kind)
