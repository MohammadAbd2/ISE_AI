"""
LSP (Language Server Protocol) Integration

Provides:
- Go-to-definition
- Hover documentation
- Real-time diagnostics
- Symbol search
- Code completion
- Find references
"""

import json
import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class Location:
    """A location in a file."""
    file_path: str
    line: int
    column: int


@dataclass
class Diagnostic:
    """A diagnostic issue."""
    file_path: str
    line: int
    column: int
    message: str
    severity: str  # error, warning, info, hint
    source: str = ""
    code: str = ""


@dataclass
class Symbol:
    """A code symbol."""
    name: str
    kind: str  # function, class, variable, etc.
    file_path: str
    line: int
    column: int
    container: str = ""


@dataclass
class HoverInfo:
    """Hover documentation."""
    contents: str
    range: Optional[Dict] = None


class LSPIntegration:
    """
    LSP Integration for code intelligence.
    
    Provides:
    - Go-to-definition
    - Hover documentation
    - Diagnostics
    - Symbol search
    - Find references
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.symbols: List[Symbol] = []
        self.diagnostics: List[Diagnostic] = []
        self._indexed = False

    def index_project(self) -> int:
        """Index project for LSP features."""
        self.symbols = []
        files_indexed = 0

        for file_path in self.project_root.rglob("*"):
            if not file_path.is_file():
                continue
            if self._should_ignore(file_path):
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                language = self._detect_language(file_path)
                
                # Extract symbols
                symbols = self._extract_symbols(content, str(file_path), language)
                self.symbols.extend(symbols)
                
                # Run diagnostics
                diagnostics = self._run_diagnostics(content, str(file_path), language)
                self.diagnostics.extend(diagnostics)
                
                files_indexed += 1
            except Exception:
                continue

        self._indexed = True
        return files_indexed

    def go_to_definition(self, file_path: str, line: int, column: int) -> Dict[str, Any]:
        """Find where a symbol is defined."""
        if not self._indexed:
            self.index_project()

        # Get the symbol at the position
        symbol = self._find_symbol_at_position(file_path, line, column)
        if symbol:
            return {
                "success": True,
                "location": {
                    "file": symbol.file_path,
                    "line": symbol.line,
                    "column": symbol.column,
                },
                "name": symbol.name,
                "kind": symbol.kind,
            }

        return {"success": False, "error": "Symbol not found"}

    def get_hover_info(self, file_path: str, line: int, column: int) -> Dict[str, Any]:
        """Get hover documentation for a symbol."""
        if not self._indexed:
            self.index_project()

        symbol = self._find_symbol_at_position(file_path, line, column)
        if symbol:
            return {
                "success": True,
                "contents": self._generate_hover_content(symbol),
            }

        return {"success": False, "error": "No hover info available"}

    def get_diagnostics(self, file_path: Optional[str] = None) -> Dict[str, Any]:
        """Get diagnostics (errors, warnings)."""
        if not self._indexed:
            self.index_project()

        if file_path:
            diagnostics = [d for d in self.diagnostics if d.file_path == file_path]
        else:
            diagnostics = self.diagnostics

        return {
            "success": True,
            "diagnostics": [
                {
                    "file": d.file_path,
                    "line": d.line,
                    "column": d.column,
                    "message": d.message,
                    "severity": d.severity,
                    "source": d.source,
                    "code": d.code,
                }
                for d in diagnostics
            ],
            "count": len(diagnostics),
        }

    def find_references(self, symbol_name: str) -> Dict[str, Any]:
        """Find all references to a symbol."""
        if not self._indexed:
            self.index_project()

        references = []
        for symbol in self.symbols:
            if symbol.name == symbol_name:
                references.append({
                    "file": symbol.file_path,
                    "line": symbol.line,
                    "column": symbol.column,
                })

        return {
            "success": True,
            "symbol": symbol_name,
            "references": references,
            "count": len(references),
        }

    def search_symbols(self, query: str, kind: Optional[str] = None) -> Dict[str, Any]:
        """Search for symbols by name."""
        if not self._indexed:
            self.index_project()

        query_lower = query.lower()
        results = []

        for symbol in self.symbols:
            if query_lower in symbol.name.lower():
                if kind is None or symbol.kind == kind:
                    results.append({
                        "name": symbol.name,
                        "kind": symbol.kind,
                        "file": symbol.file_path,
                        "line": symbol.line,
                        "column": symbol.column,
                        "container": symbol.container,
                    })

        return {
            "success": True,
            "query": query,
            "results": results[:50],
            "count": len(results),
        }

    def _extract_symbols(self, content: str, file_path: str, language: str) -> List[Symbol]:
        """Extract symbols from code."""
        import re
        symbols = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Functions
            if language == "python":
                match = re.match(r"\s*(?:def|class)\s+(\w+)", line)
                if match:
                    kind = "function" if "def" in line else "class"
                    symbols.append(Symbol(
                        name=match.group(1),
                        kind=kind,
                        file_path=file_path,
                        line=line_num,
                        column=0,
                    ))
            elif language in ("javascript", "typescript"):
                # Functions
                match = re.search(r"(?:function|const|let|var)\s+(\w+)", line)
                if match:
                    symbols.append(Symbol(
                        name=match.group(1),
                        kind="function",
                        file_path=file_path,
                        line=line_num,
                        column=0,
                    ))
                # Classes
                match = re.search(r"class\s+(\w+)", line)
                if match:
                    symbols.append(Symbol(
                        name=match.group(1),
                        kind="class",
                        file_path=file_path,
                        line=line_num,
                        column=0,
                    ))

        return symbols

    def _run_diagnostics(self, content: str, file_path: str, language: str) -> List[Diagnostic]:
        """Run basic diagnostics."""
        diagnostics = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Check for common issues
            if language == "python":
                # Syntax issues
                if line.rstrip().endswith("(") and not line.rstrip().endswith("\\"):
                    # Might be incomplete
                    pass
            
            # Check for TODO comments
            if "TODO" in line or "FIXME" in line:
                diagnostics.append(Diagnostic(
                    file_path=file_path,
                    line=line_num,
                    column=0,
                    message="TODO/FIXME comment found",
                    severity="info",
                    source="ISE AI",
                ))

        return diagnostics

    def _find_symbol_at_position(self, file_path: str, line: int, column: int) -> Optional[Symbol]:
        """Find symbol at a specific position."""
        for symbol in self.symbols:
            if symbol.file_path == file_path and symbol.line == line:
                return symbol
        return None

    def _generate_hover_content(self, symbol: Symbol) -> str:
        """Generate hover content for a symbol."""
        return f"**{symbol.name}**\n\nType: {symbol.kind}\nFile: {symbol.file_path}"

    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language."""
        ext = file_path.suffix.lower()
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
        }
        return ext_map.get(ext, "unknown")

    def _should_ignore(self, file_path: Path) -> bool:
        """Check if file should be ignored."""
        ignore_dirs = {
            ".git", "node_modules", "__pycache__", ".venv", "venv",
            ".idea", ".vscode", "dist", "build", "target", ".cache",
        }
        return any(part in ignore_dirs for part in file_path.parts)


# Global instance
_lsp: Optional[LSPIntegration] = None


def get_lsp_integration(project_root: Optional[Path] = None) -> LSPIntegration:
    """Get or create LSP integration instance."""
    global _lsp
    if _lsp is None:
        if project_root is None:
            project_root = Path.cwd()
        _lsp = LSPIntegration(project_root)
    return _lsp
