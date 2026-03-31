"""
Enhanced API Routes for Advanced Features

Provides endpoints for:
- Terminal commands
- Git operations
- RAG search
- Confirmation management
- Voice commands
- File operations
- Code review
"""

import json
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from pathlib import Path

from backend.app.services.terminal import get_terminal_integration
from backend.app.services.git_integration import get_git_integration
from backend.app.services.enhanced_rag import get_enhanced_rag_context
from backend.app.services.confirmation import get_confirmation_manager, ConfirmationStatus
from backend.app.services.style_learner import get_style_learner
from backend.app.core.config import settings

router = APIRouter()

# Request/Response Models

class TerminalRequest(BaseModel):
    command: str
    timeout: int = 120

class TerminalResponse(BaseModel):
    command: str
    stdout: str
    stderr: str
    return_code: int
    error_analysis: Optional[dict] = None
    suggested_fix: Optional[str] = None

class GitStatusResponse(BaseModel):
    branch: str
    staged_changes: list[str]
    unstaged_changes: list[str]
    untracked_files: list[str]
    is_clean: bool

class CommitRequest(BaseModel):
    message: str
    files: Optional[list[str]] = None

class RAGSearchRequest(BaseModel):
    query: str
    limit: int = 10

class RAGSearchResponse(BaseModel):
    results: list[dict]

class ConfirmationResponseRequest(BaseModel):
    confirmation_id: str
    response: str
    allow_always: bool = False

class VoiceCommandRequest(BaseModel):
    transcript: str
    context: Optional[dict] = None

class FileOperationRequest(BaseModel):
    operation: str  # read, write, delete, move
    path: str
    content: Optional[str] = None
    new_path: Optional[str] = None

class CodeReviewRequest(BaseModel):
    file_path: str
    content: str

# Terminal Endpoints

@router.post("/api/terminal/run", response_model=TerminalResponse)
async def run_terminal_command(request: TerminalRequest):
    """Run a terminal command and return output."""
    terminal = get_terminal_integration()
    result = await terminal.run_command(request.command, request.timeout)
    
    return TerminalResponse(
        command=result.command,
        stdout=result.stdout,
        stderr=result.stderr,
        return_code=result.return_code,
        error_analysis=result.error_analysis,
        suggested_fix=result.suggested_fix,
    )

@router.get("/api/terminal/suggest-command")
async def suggest_command(file_path: str):
    """Suggest command to run a file."""
    terminal = get_terminal_integration()
    command = terminal.get_run_command(file_path)
    return {"command": command}

# Git Endpoints

@router.get("/api/git/status", response_model=GitStatusResponse)
async def get_git_status():
    """Get git repository status."""
    git = get_git_integration()
    if not git.is_git_repo():
        raise HTTPException(status_code=400, detail="Not a git repository")
    
    status = await git.get_status()
    return GitStatusResponse(
        branch=status.branch,
        staged_changes=status.staged_changes,
        unstaged_changes=status.unstaged_changes,
        untracked_files=status.untracked_files,
        is_clean=status.is_clean,
    )

@router.post("/api/git/commit-message")
async def generate_commit_message():
    """Generate commit message based on staged changes."""
    git = get_git_integration()
    if not git.is_git_repo():
        raise HTTPException(status_code=400, detail="Not a git repository")
    
    suggestion = await git.generate_commit_message()
    return {
        "message": suggestion.message,
        "description": suggestion.description,
        "type": suggestion.type,
        "files": suggestion.files,
    }

@router.post("/api/git/pr-description")
async def generate_pr_description(
    title: str = "Pull Request",
    branch_from: str = "",
    branch_to: str = "main"
):
    """Generate PR description."""
    git = get_git_integration()
    if not git.is_git_repo():
        raise HTTPException(status_code=400, detail="Not a git repository")
    
    description = await git.generate_pr_description(title, branch_from, branch_to)
    return {"description": description}

@router.get("/api/git/recent-commits")
async def get_recent_commits(count: int = 5):
    """Get recent commit messages."""
    git = get_git_integration()
    commits = await git.get_recent_commits(count)
    return {"commits": commits}

# RAG Search Endpoints

@router.post("/api/rag/search", response_model=RAGSearchResponse)
async def rag_search(request: RAGSearchRequest):
    """Search codebase using semantic search."""
    rag = get_enhanced_rag_context()
    results = rag.semantic_search(request.query, request.limit)
    
    return RAGSearchResponse(
        results=[
            {
                "file_path": r.file_path,
                "content": r.content[:500],  # Truncate for response
                "score": r.score,
                "match_type": r.match_type,
                "line_number": r.line_number,
            }
            for r in results
        ]
    )

@router.get("/api/rag/symbol/{symbol_name}")
async def find_symbol(symbol_name: str):
    """Find a symbol by name."""
    rag = get_enhanced_rag_context()
    symbol = rag.find_symbol(symbol_name)
    
    if not symbol:
        raise HTTPException(status_code=404, detail="Symbol not found")
    
    return {
        "name": symbol.name,
        "type": symbol.symbol_type,
        "file_path": symbol.file_path,
        "line_start": symbol.line_start,
        "signature": symbol.signature,
    }

@router.get("/api/rag/references/{symbol_name}")
async def find_references(symbol_name: str):
    """Find all references to a symbol."""
    rag = get_enhanced_rag_context()
    references = rag.find_references(symbol_name)
    return {"references": references}

# Confirmation Endpoints

@router.post("/api/confirmation/respond")
async def respond_to_confirmation(request: ConfirmationResponseRequest):
    """Respond to a confirmation request."""
    manager = get_confirmation_manager()
    
    try:
        confirmation = await manager.respond_to_confirmation(
            request.confirmation_id,
            request.response,
            request.allow_always,
        )
        
        return {
            "status": confirmation.status.value,
            "approved": confirmation.status in [ConfirmationStatus.APPROVED, ConfirmationStatus.APPROVED_ALWAYS],
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/api/confirmation/pending")
async def get_pending_confirmations():
    """Get all pending confirmation requests."""
    manager = get_confirmation_manager()
    confirmations = manager.get_pending_confirmations()
    
    return {
        "confirmations": [
            manager.format_confirmation_message(c)
            for c in confirmations
        ]
    }

# Style Learner Endpoints

@router.get("/api/style/profile")
async def get_style_profile():
    """Get user's coding style profile."""
    learner = get_style_learner()
    await learner.load_preferences()
    
    return {
        "variable_naming": learner.profile.variable_naming,
        "function_naming": learner.profile.function_naming,
        "class_naming": learner.profile.class_naming,
        "prefer_async": learner.profile.prefer_async,
        "prefer_type_hints": learner.profile.prefer_type_hints,
        "common_imports": learner.profile.common_imports,
    }

@router.post("/api/style/learn")
async def learn_from_codebase():
    """Trigger style learning from codebase."""
    learner = get_style_learner()
    await learner.learn_from_codebase()
    return {"status": "learned", "files_analyzed": len(learner.profile.learned_from_files)}

# File Operations Endpoints

@router.post("/api/files/operation")
async def file_operation(request: FileOperationRequest):
    """Perform file operations (read, write, delete, move)."""
    from backend.app.services.autonomous_agent import get_autonomous_agent
    
    agent = get_autonomous_agent()
    
    try:
        if request.operation == "read":
            content = await agent.fs.read_file(request.path)
            return {"success": content[0], "content": content[1] if content[0] else None}
        
        elif request.operation == "write":
            if not request.content:
                raise HTTPException(status_code=400, detail="Content required for write operation")
            result = await agent.fs.write_file(request.path, request.content)
            return {"success": result[0], "message": result[1]}
        
        elif request.operation == "delete":
            path = agent.fs._resolve_path(request.path)
            if path.exists():
                path.unlink()
                return {"success": True, "message": f"Deleted {request.path}"}
            return {"success": False, "message": "File not found"}
        
        elif request.operation == "move":
            if not request.new_path:
                raise HTTPException(status_code=400, detail="new_path required for move operation")
            path = agent.fs._resolve_path(request.path)
            new_path = agent.fs._resolve_path(request.new_path)
            path.rename(new_path)
            return {"success": True, "message": f"Moved {request.path} to {request.new_path}"}
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown operation: {request.operation}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Code Review Endpoint

@router.post("/api/code/review")
async def code_review(request: CodeReviewRequest):
    """Get AI-powered code review."""
    from backend.app.services.chat import get_chat_service
    
    chat_service = get_chat_service()
    
    review_prompt = f"""Please review this code and provide feedback on:
1. Code quality and best practices
2. Potential bugs or issues
3. Performance considerations
4. Security concerns
5. Suggestions for improvement

File: {request.file_path}

Code:
```
{request.content}
```

Provide a detailed review with specific suggestions."""

    from backend.app.models.message import Message
    messages = [Message(role="user", content=review_prompt)]
    
    try:
        review = await chat_service.provider.generate(
            messages=messages,
            model=settings.default_model,
            options={"temperature": 0.2, "num_predict": 2048}
        )
        
        return {
            "file_path": request.file_path,
            "review": review,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Review failed: {str(e)}")

# Voice Command Processing

@router.post("/api/voice/process")
async def process_voice_command(request: VoiceCommandRequest):
    """Process voice command transcript and return action."""
    transcript = request.transcript.lower()
    
    # Detect command type
    command_type = "unknown"
    action = None
    
    if any(word in transcript for word in ["create", "make", "add"]):
        command_type = "create"
        action = "agent"
    elif any(word in transcript for word in ["open", "show", "view"]):
        command_type = "open"
        action = "navigate"
    elif any(word in transcript for word in ["run", "execute", "test"]):
        command_type = "run"
        action = "terminal"
    elif any(word in transcript for word in ["save", "write", "update"]):
        command_type = "save"
        action = "file_operation"
    elif any(word in transcript for word in ["delete", "remove"]):
        command_type = "delete"
        action = "file_operation"
    elif any(word in transcript for word in ["search", "find"]):
        command_type = "search"
        action = "rag_search"
    elif any(word in transcript for word in ["commit", "push", "git"]):
        command_type = "git"
        action = "git_operation"
    
    return {
        "transcript": request.transcript,
        "command_type": command_type,
        "action": action,
        "confidence": 0.8,  # Would use ML model in production
        "suggested_params": extract_command_params(transcript, command_type),
    }

def extract_command_params(transcript: str, command_type: str) -> dict:
    """Extract parameters from voice command."""
    import re
    
    params = {}
    
    # Extract file paths
    path_match = re.search(r'(?:in|at|to|from)\s+([\w/\.]+\.\w+)', transcript)
    if path_match:
        params['path'] = path_match.group(1)
    
    # Extract file names
    name_match = re.search(r'(?:called|named|file)\s+([\w\-]+\.\w+)', transcript)
    if name_match:
        params['filename'] = name_match.group(1)
    
    # Extract search queries
    if command_type == "search":
        query_match = re.search(r'(?:for|about)\s+(.+)', transcript)
        if query_match:
            params['query'] = query_match.group(1)
    
    return params

# Project Search and Replace

@router.post("/api/project/search-replace")
async def project_search_replace(
    search: str,
    replace: str,
    glob_pattern: str = "**/*.py",
    dry_run: bool = True
):
    """Search and replace across project."""
    from backend.app.services.autonomous_agent import get_autonomous_agent
    
    agent = get_autonomous_agent()
    
    matches = []
    for path in agent.project_root.glob(glob_pattern):
        if path.is_file():
            try:
                content = path.read_text(encoding="utf-8")
                if search in content:
                    matches.append({
                        "file": str(path.relative_to(agent.project_root)),
                        "occurrences": content.count(search),
                    })
            except:
                pass
    
    if dry_run:
        return {
            "dry_run": True,
            "matches": matches,
            "total_files": len(matches),
        }
    
    # Perform replacement
    modified_files = []
    for match in matches:
        file_path = agent.project_root / match["file"]
        content = file_path.read_text(encoding="utf-8")
        new_content = content.replace(search, replace)
        file_path.write_text(new_content, encoding="utf-8")
        modified_files.append(match["file"])
    
    return {
        "dry_run": False,
        "modified_files": modified_files,
        "total_modified": len(modified_files),
    }

# Cache and Performance

@router.post("/api/cache/clear")
async def clear_cache():
    """Clear various caches."""
    from backend.app.services.enhanced_rag import _rag_context
    from backend.app.services.style_learner import _style_learner
    from backend.app.services.confirmation import _confirmation_manager
    
    cleared = []
    
    if _rag_context:
        _rag_context.index = {}
        _rag_context.content_cache = {}
        cleared.append("RAG index")
    
    if _style_learner:
        _style_learner.profile = _style_learner.__class__(_style_learner.project_root).profile
        cleared.append("Style profile")
    
    if _confirmation_manager:
        _confirmation_manager.pending_confirmations = {}
        cleared.append("Confirmations")
    
    return {"cleared": cleared}

@router.get("/api/stats")
async def get_stats():
    """Get system statistics."""
    from backend.app.services.enhanced_rag import _rag_context
    
    stats = {
        "rag_indexed_files": len(_rag_context.index) if _rag_context else 0,
        "rag_symbols": len(_rag_context.symbol_graph) if _rag_context else 0,
        "memory_usage_mb": 0,  # Would use psutil in production
    }
    
    return stats
