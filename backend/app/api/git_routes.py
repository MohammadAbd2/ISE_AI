"""
Git API Routes

Exposes git operations via REST API for use by:
- Frontend UI
- IDE extensions
- AI agents
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
from typing import Optional

from app.services.git_integration import get_git_integration

router = APIRouter(prefix="/api/git", tags=["git"])


class GitStatusResponse(BaseModel):
    branch: str
    is_clean: bool
    staged_changes: list[str]
    unstaged_changes: list[str]
    untracked_files: list[str]
    ahead: int
    behind: int


class CommitRequest(BaseModel):
    message: str
    files: Optional[list[str]] = None


class BranchRequest(BaseModel):
    name: str
    from_branch: Optional[str] = None


class CheckoutRequest(BaseModel):
    branch: str


class PushPullRequest(BaseModel):
    remote: str = "origin"
    branch: Optional[str] = None


@router.get("/status")
async def get_status():
    """Get git repository status."""
    git = get_git_integration()
    
    if not git or not git.is_git_repo():
        raise HTTPException(status_code=404, detail="Not a git repository")
    
    status = await git.get_status()
    
    return {
        "success": True,
        "branch": status.branch,
        "is_clean": status.is_clean,
        "staged_changes": status.staged_changes,
        "unstaged_changes": status.unstaged_changes,
        "untracked_files": status.untracked_files,
        "ahead": status.ahead,
        "behind": status.behind,
    }


@router.get("/branches")
async def list_branches():
    """List all git branches."""
    git = get_git_integration()
    
    if not git or not git.is_git_repo():
        raise HTTPException(status_code=404, detail="Not a git repository")
    
    branches = await git.list_branches()
    
    return {
        "success": True,
        "branches": branches,
    }


@router.post("/branch/create")
async def create_branch(request: BranchRequest):
    """Create a new git branch."""
    git = get_git_integration()
    
    if not git or not git.is_git_repo():
        raise HTTPException(status_code=404, detail="Not a git repository")
    
    success = await git.create_branch(request.name, request.from_branch or "")
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create branch")
    
    return {
        "success": True,
        "message": f"Branch '{request.name}' created",
    }


@router.post("/branch/checkout")
async def checkout_branch(request: CheckoutRequest):
    """Switch to a git branch."""
    git = get_git_integration()
    
    if not git or not git.is_git_repo():
        raise HTTPException(status_code=404, detail="Not a git repository")
    
    success = await git.checkout_branch(request.branch)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to checkout branch")
    
    return {
        "success": True,
        "message": f"Switched to branch '{request.branch}'",
    }


@router.post("/commit")
async def commit_changes(request: CommitRequest):
    """Stage files and commit with message."""
    git = get_git_integration()
    
    if not git or not git.is_git_repo():
        raise HTTPException(status_code=404, detail="Not a git repository")
    
    # Stage files if provided
    if request.files:
        staged = await git.stage_files(request.files)
        if not staged:
            raise HTTPException(status_code=500, detail="Failed to stage files")
    
    # Commit
    success = await git.commit(request.message)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to commit")
    
    return {
        "success": True,
        "message": f"Committed: {request.message}",
    }


@router.post("/stage")
async def stage_files(files: list[str]):
    """Stage files for commit."""
    git = get_git_integration()
    
    if not git or not git.is_git_repo():
        raise HTTPException(status_code=404, detail="Not a git repository")
    
    success = await git.stage_files(files)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to stage files")
    
    return {
        "success": True,
        "message": f"Staged {len(files)} file(s)",
    }


@router.post("/push")
async def push_to_remote(request: PushPullRequest):
    """Push to remote repository."""
    git = get_git_integration()
    
    if not git or not git.is_git_repo():
        raise HTTPException(status_code=404, detail="Not a git repository")
    
    success = await git.push(request.remote, request.branch or "")
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to push")
    
    return {
        "success": True,
        "message": "Pushed to remote",
    }


@router.post("/pull")
async def pull_from_remote(request: PushPullRequest):
    """Pull from remote repository."""
    git = get_git_integration()
    
    if not git or not git.is_git_repo():
        raise HTTPException(status_code=404, detail="Not a git repository")
    
    success = await git.pull(request.remote, request.branch or "")
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to pull")
    
    return {
        "success": True,
        "message": "Pulled from remote",
    }


@router.get("/diff")
async def get_diff(file_path: Optional[str] = ""):
    """Get unstaged diff."""
    git = get_git_integration()
    
    if not git or not git.is_git_repo():
        raise HTTPException(status_code=404, detail="Not a git repository")
    
    diff = await git.get_diff(file_path or "")
    
    return {
        "success": True,
        "diff": diff,
    }


@router.get("/log")
async def get_log(count: int = 20):
    """Get git log."""
    git = get_git_integration()
    
    if not git or not git.is_git_repo():
        raise HTTPException(status_code=404, detail="Not a git repository")
    
    commits = await git.get_log(count)
    
    return {
        "success": True,
        "commits": commits,
        "count": len(commits),
    }


@router.get("/blame/{file_path:path}")
async def get_blame(file_path: str):
    """Get git blame for a file."""
    git = get_git_integration()
    
    if not git or not git.is_git_repo():
        raise HTTPException(status_code=404, detail="Not a git repository")
    
    blames = await git.blame(file_path)
    
    return {
        "success": True,
        "blames": blames,
        "file": file_path,
    }


@router.get("/commit-suggestion")
async def suggest_commit_message():
    """Suggest a commit message based on current changes."""
    git = get_git_integration()
    
    if not git or not git.is_git_repo():
        raise HTTPException(status_code=404, detail="Not a git repository")
    
    suggestion = await git.generate_commit_message()
    
    return {
        "success": True,
        "message": suggestion.message,
        "type": suggestion.type,
        "description": suggestion.description,
    }


@router.get("/pr-description")
async def generate_pr_description(
    title: str = "",
    branch_from: str = "",
    branch_to: str = "main"
):
    """Generate a PR description."""
    git = get_git_integration()
    
    if not git or not git.is_git_repo():
        raise HTTPException(status_code=404, detail="Not a git repository")
    
    description = await git.generate_pr_description(title, branch_from, branch_to)
    
    return {
        "success": True,
        "description": description,
    }
