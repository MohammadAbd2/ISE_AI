"""
Embedded Browser API Routes

Provides UI debugging capabilities
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.embedded_browser import get_embedded_browser

router = APIRouter(prefix="/api/browser", tags=["browser"])


class CreateBrowserSession(BaseModel):
    session_id: str
    url: Optional[str] = ""


class NavigateRequest(BaseModel):
    session_id: str
    url: str


class TestScript(BaseModel):
    session_id: str
    script: str


@router.post("/session/create")
async def create_session(request: CreateBrowserSession):
    """Create a new browser session."""
    browser = get_embedded_browser()
    result = await browser.create_session(request.session_id, request.url or "")
    return result


@router.post("/navigate")
async def navigate(request: NavigateRequest):
    """Navigate to a URL."""
    browser = get_embedded_browser()
    result = await browser.navigate(request.session_id, request.url)
    return result


@router.post("/screenshot")
async def screenshot(session_id: str, full_page: bool = False):
    """Capture a screenshot."""
    browser = get_embedded_browser()
    result = await browser.screenshot(session_id, full_page)
    return result


@router.get("/dom")
async def get_dom(session_id: str):
    """Get DOM tree."""
    browser = get_embedded_browser()
    result = await browser.get_dom(session_id)
    return result


@router.get("/query")
async def query_selector(session_id: str, selector: str):
    """Find element by CSS selector."""
    browser = get_embedded_browser()
    result = await browser.query_selector(session_id, selector)
    return result


@router.post("/click")
async def click_element(session_id: str, selector: str):
    """Click an element."""
    browser = get_embedded_browser()
    result = await browser.click_element(session_id, selector)
    return result


@router.get("/console")
async def get_console_logs(session_id: str):
    """Get console logs."""
    browser = get_embedded_browser()
    result = await browser.get_console_logs(session_id)
    return result


@router.post("/test")
async def run_test(request: TestScript):
    """Run a UI test."""
    browser = get_embedded_browser()
    result = await browser.run_test(request.session_id, request.script)
    return result


@router.post("/session/close")
async def close_session(session_id: str):
    """Close a browser session."""
    browser = get_embedded_browser()
    result = await browser.close_session(session_id)
    return result


@router.get("/sessions")
async def list_sessions():
    """List all browser sessions."""
    browser = get_embedded_browser()
    return browser.list_sessions()
