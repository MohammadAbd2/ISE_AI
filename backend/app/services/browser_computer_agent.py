from __future__ import annotations
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

@dataclass(slots=True)
class BrowserAction:
    action: str; target: str = ''; value: str = ''; status: str = 'pending'; output: str = ''
    def to_dict(self) -> dict[str, Any]: return asdict(self)
@dataclass(slots=True)
class BrowserRun:
    id: str; url: str; status: str = 'created'; actions: list[BrowserAction] = field(default_factory=list); screenshot_path: str | None = None; error: str = ''
    def to_dict(self) -> dict[str, Any]: return asdict(self)
class BrowserComputerAgent:
    async def smoke_test(self, url: str, *, expect_text: str | None = None, output_dir: str | Path | None = None) -> BrowserRun:
        run=BrowserRun(id=str(uuid4()), url=url, status='running')
        out=Path(output_dir or Path.home()/'.cache'/'ise_ai'/'browser').expanduser().resolve(); out.mkdir(parents=True, exist_ok=True)
        try:
            from playwright.async_api import async_playwright  # type: ignore
        except Exception as exc:
            run.status='blocked'; run.error=f'Playwright unavailable: {exc}'; return run
        try:
            async with async_playwright() as p:
                browser=await p.chromium.launch(headless=True)
                page=await browser.new_page(viewport={'width':1366,'height':900})
                a=BrowserAction('goto', url); run.actions.append(a)
                await page.goto(url, wait_until='networkidle', timeout=30000); a.status='completed'; a.output=page.url
                if expect_text:
                    c=BrowserAction('expect_text', expect_text); run.actions.append(c); body=await page.inner_text('body')
                    c.status='completed' if expect_text.lower() in body.lower() else 'failed'; c.output='Text found' if c.status=='completed' else 'Text not found'
                    if c.status=='failed': run.status='failed'
                shot=out/f'browser-{run.id}.png'; await page.screenshot(path=str(shot), full_page=True); run.screenshot_path=str(shot)
                await browser.close(); run.status = run.status if run.status=='failed' else 'passed'
        except Exception as exc:
            run.status='failed'; run.error=str(exc)
        return run
_browser_agent=BrowserComputerAgent()
def get_browser_computer_agent() -> BrowserComputerAgent: return _browser_agent
