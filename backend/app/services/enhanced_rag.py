"""
Enhanced RAG with Semantic Search and Embeddings

Provides:
- Semantic search using embeddings
- Cross-file reference tracking
- Symbol graph for code navigation
- Large context support (100K+ tokens)
"""

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

import aiofiles
import httpx

from app.core.config import settings


@dataclass
class CodeSymbol:
    """Represents a code symbol (function, class, variable, etc.)."""
    name: str
    symbol_type: str  # function, class, variable, import, etc.
    file_path: str
    line_start: int
    line_end: int
    signature: str = ""
    docstring: str = ""
    references: list[str] = field(default_factory=list)  # Files that reference this symbol


@dataclass
class FileEmbedding:
    """Embedding data for a file."""
    file_path: str
    content_hash: str
    embedding: list[float] = field(default_factory=list)
    chunks: list[dict] = field(default_factory=list)  # Chunked content with embeddings
    indexed_at: str = ""


@dataclass
class SearchResult:
    """A search result item."""
    file_path: str
    content: str
    score: float
    match_type: str  # semantic, keyword, symbol
    line_number: int = 0


class EnhancedRAGContext:
    """
    Enhanced RAG system with semantic search and code understanding.
    
    Similar to Claude Code's and Cursor's codebase understanding.
    """
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.file_index: dict[str, dict] = {}  # file_path -> metadata
        self.symbol_graph: dict[str, CodeSymbol] = {}  # symbol_name -> CodeSymbol
        self.embeddings: dict[str, FileEmbedding] = {}  # file_path -> embedding
        self.reference_map: dict[str, set[str]] = {}  # symbol -> files that reference it
        self.content_cache: dict[str, str] = {}  # file_path -> content
        
        # Configuration
        self.max_file_size = 500000  # 500KB max per file
        self.chunk_size = 2000  # Characters per chunk for embeddings
        self.max_context_tokens = 100000  # Target context window
    
    async def build_index(self):
        """Build comprehensive index of the project."""
        await self._index_all_files()
        await self._extract_symbols()
        await self._build_reference_map()
    
    async def _index_all_files(self):
        """Index all source files in the project."""
        exclude_dirs = {
            ".git", "node_modules", "__pycache__", ".venv", "venv",
            ".evolution-backups", "dist", "build", ".next", "coverage",
            ".idea", ".vscode", "target", "bin", "obj"
        }
        exclude_extensions = {
            ".pyc", ".pyo", ".so", ".dll", ".exe", ".bin", ".dat",
            ".lock", ".log", ".bak", ".swp", ".swo"
        }
        
        for path in self.project_root.rglob("*"):
            if path.is_file():
                # Check exclusions
                if any(exclude in str(path) for exclude in exclude_dirs):
                    continue
                if path.suffix in exclude_extensions:
                    continue
                
                rel_path = str(path.relative_to(self.project_root))
                
                # Index content for text files
                if path.suffix in {".py", ".js", ".jsx", ".ts", ".tsx", ".json", 
                                   ".md", ".txt", ".html", ".css", ".scss", ".sql", ".yaml", ".yml"}:
                    try:
                        content = path.read_text(encoding="utf-8")
                        if len(content) < self.max_file_size:
                            content_hash = hashlib.sha256(content.encode()).hexdigest()
                            
                            self.file_index[rel_path] = {
                                "path": rel_path,
                                "size": len(content),
                                "lines": content.count("\n") + 1,
                                "hash": content_hash,
                                "type": self._get_file_type(path.suffix),
                                "indexed_at": datetime.now(UTC).isoformat(),
                            }
                            
                            self.content_cache[rel_path] = content
                    except Exception:
                        pass
    
    def _get_file_type(self, extension: str) -> str:
        """Get file type category."""
        type_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript-react",
            ".ts": "typescript",
            ".tsx": "typescript-react",
            ".html": "html",
            ".css": "css",
            ".scss": "scss",
            ".json": "json",
            ".md": "markdown",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".sql": "sql",
        }
        return type_map.get(extension, "text")
    
    async def _extract_symbols(self):
        """Extract symbols (functions, classes, etc.) from all files."""
        for file_path, content in self.content_cache.items():
            file_type = self.file_index.get(file_path, {}).get("type", "")
            
            if file_type == "python":
                symbols = self._extract_python_symbols(file_path, content)
            elif file_type in ["javascript", "typescript", "javascript-react", "typescript-react"]:
                symbols = self._extract_js_symbols(file_path, content)
            else:
                symbols = []
            
            for symbol in symbols:
                self.symbol_graph[symbol.name] = symbol
    
    def _extract_python_symbols(self, file_path: str, content: str) -> list[CodeSymbol]:
        """Extract Python symbols (functions, classes)."""
        symbols = []
        
        # Find functions
        func_pattern = r"(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)\s*(?:->\s*([^\n:]+))?:"
        for match in re.finditer(func_pattern, content):
            name = match.group(1)
            params = match.group(2)
            return_type = match.group(3) or "None"
            
            # Find line numbers
            line_start = content[:match.start()].count("\n") + 1
            
            symbols.append(CodeSymbol(
                name=name,
                symbol_type="function",
                file_path=file_path,
                line_start=line_start,
                line_end=line_start,  # Would need more logic for end line
                signature=f"def {name}({params}) -> {return_type}",
            ))
        
        # Find classes
        class_pattern = r"class\s+(\w+)(?:\s*\(\s*([^)]+)\s*\))?:"
        for match in re.finditer(class_pattern, content):
            name = match.group(1)
            bases = match.group(2) or ""
            line_start = content[:match.start()].count("\n") + 1
            
            symbols.append(CodeSymbol(
                name=name,
                symbol_type="class",
                file_path=file_path,
                line_start=line_start,
                line_end=line_start,
                signature=f"class {name}({bases})" if bases else f"class {name}",
            ))
        
        return symbols
    
    def _extract_js_symbols(self, file_path: str, content: str) -> list[CodeSymbol]:
        """Extract JavaScript/TypeScript symbols."""
        symbols = []
        
        # Find functions
        func_pattern = r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)"
        for match in re.finditer(func_pattern, content):
            name = match.group(1)
            params = match.group(2)
            line_start = content[:match.start()].count("\n") + 1
            
            symbols.append(CodeSymbol(
                name=name,
                symbol_type="function",
                file_path=file_path,
                line_start=line_start,
                line_end=line_start,
                signature=f"function {name}({params})",
            ))
        
        # Find arrow functions assigned to variables
        arrow_pattern = r"(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(([^)]*)\)\s*=>"
        for match in re.finditer(arrow_pattern, content):
            name = match.group(1)
            params = match.group(2)
            line_start = content[:match.start()].count("\n") + 1
            
            symbols.append(CodeSymbol(
                name=name,
                symbol_type="function",
                file_path=file_path,
                line_start=line_start,
                line_end=line_start,
                signature=f"const {name} = ({params}) => ...",
            ))
        
        # Find classes
        class_pattern = r"(?:export\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?"
        for match in re.finditer(class_pattern, content):
            name = match.group(1)
            extends = match.group(2) or ""
            line_start = content[:match.start()].count("\n") + 1
            
            symbols.append(CodeSymbol(
                name=name,
                symbol_type="class",
                file_path=file_path,
                line_start=line_start,
                line_end=line_start,
                signature=f"class {name}" + (f" extends {extends}" if extends else ""),
            ))
        
        return symbols
    
    async def _build_reference_map(self):
        """Build map of which files reference which symbols."""
        for symbol_name, symbol in self.symbol_graph.items():
            self.reference_map[symbol_name] = set()
            
            # Search for references in all files
            for file_path, content in self.content_cache.items():
                if file_path == symbol.file_path:
                    continue  # Skip the file where symbol is defined
                
                # Simple text search for symbol name
                if re.search(rf"\b{re.escape(symbol_name)}\b", content):
                    self.reference_map[symbol_name].add(file_path)
                    symbol.references.append(file_path)
    
    def semantic_search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """
        Search for relevant code using semantic similarity.
        
        When embeddings are available (via Ollama), uses vector similarity.
        Falls back to keyword + symbol search otherwise.
        """
        results = []
        
        # Try semantic search with embeddings first
        try:
            embedding_results = self._semantic_search_with_embedding(query, limit)
            if embedding_results:
                return embedding_results
        except Exception:
            pass
        
        # Fallback to keyword + symbol search
        results.extend(self._keyword_search(query, limit // 2))
        results.extend(self._symbol_search(query, limit // 2))
        
        # Deduplicate and sort by score
        seen = set()
        unique_results = []
        for result in sorted(results, key=lambda r: r.score, reverse=True):
            if result.file_path not in seen:
                seen.add(result.file_path)
                unique_results.append(result)
        
        return unique_results[:limit]
    
    def _semantic_search_with_embedding(self, query: str, limit: int) -> list[SearchResult]:
        """Search using embeddings (requires Ollama with embedding model)."""
        # Generate embedding for query
        embedding = self._generate_embedding(query)
        if not embedding:
            return []
        
        # Compare with file embeddings
        scored_files = []
        for file_path, file_emb in self.embeddings.items():
            if file_emb.embedding:
                similarity = self._cosine_similarity(embedding, file_emb.embedding)
                if similarity > 0.3:  # Threshold
                    scored_files.append((file_path, similarity, file_emb.chunks))
        
        # Get top chunks from top files
        results = []
        for file_path, score, chunks in sorted(scored_files, key=lambda x: x[1], reverse=True)[:limit]:
            content = self.content_cache.get(file_path, "")
            results.append(SearchResult(
                file_path=file_path,
                content=content[:2000],  # First 2000 chars
                score=score,
                match_type="semantic",
            ))
        
        return results
    
    def _generate_embedding(self, text: str) -> Optional[list[float]]:
        """Generate embedding using Ollama."""
        try:
            # Use nomic-embed-text or similar embedding model
            payload = {
                "model": "nomic-embed-text",
                "prompt": text,
            }
            
            import httpx
            with httpx.AsyncClient(base_url=settings.ollama_base_url, timeout=30.0) as client:
                response = client.post("/api/embeddings", json=payload)
                if response.status_code == 200:
                    data = response.json()
                    return data.get("embedding", [])
        except Exception:
            pass
        
        return None
    
    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not vec1 or not vec2:
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _keyword_search(self, query: str, limit: int) -> list[SearchResult]:
        """Search using keyword matching."""
        query_words = set(query.lower().split())
        
        scored_files = []
        for file_path, content in self.content_cache.items():
            content_lower = content.lower()
            score = sum(1 for word in query_words if word in content_lower)
            if score > 0:
                scored_files.append((file_path, score, content))
        
        results = []
        for file_path, score, content in sorted(scored_files, key=lambda x: x[1], reverse=True)[:limit]:
            results.append(SearchResult(
                file_path=file_path,
                content=content[:2000],
                score=score / len(query_words),  # Normalize
                match_type="keyword",
            ))
        
        return results
    
    def _symbol_search(self, query: str, limit: int) -> list[SearchResult]:
        """Search for symbols matching the query."""
        results = []
        
        for symbol_name, symbol in self.symbol_graph.items():
            if query.lower() in symbol_name.lower():
                content = self.content_cache.get(symbol.file_path, "")
                # Get the symbol's code
                lines = content.split("\n")
                symbol_content = "\n".join(
                    lines[symbol.line_start-1:min(symbol.line_start+20, len(lines))]
                )
                
                results.append(SearchResult(
                    file_path=symbol.file_path,
                    content=symbol_content,
                    score=0.9,  # High score for exact symbol match
                    match_type="symbol",
                    line_number=symbol.line_start,
                ))
        
        return results[:limit]
    
    def find_symbol(self, symbol_name: str) -> Optional[CodeSymbol]:
        """Find a symbol by name."""
        return self.symbol_graph.get(symbol_name)
    
    def find_references(self, symbol_name: str) -> list[str]:
        """Find all files that reference a symbol."""
        return list(self.reference_map.get(symbol_name, set()))
    
    def get_context_for_task(self, task: str, max_tokens: int = 100000) -> str:
        """
        Get relevant context for a task, optimized for token usage.
        
        Similar to how Claude Code builds context - prioritizes relevance
        while staying within token limits.
        """
        # Search for relevant files
        search_results = self.semantic_search(task, limit=20)
        
        # Build context efficiently
        context_parts = []
        total_tokens = 0
        
        for result in search_results:
            # Estimate tokens (~4 chars per token)
            content_tokens = len(result.content) // 4
            
            if total_tokens + content_tokens > max_tokens:
                break
            
            context_parts.append(f"### File: {result.file_path}\n```\n{result.content}\n```")
            total_tokens += content_tokens
        
        return "\n\n".join(context_parts)
    
    def get_file_content(self, file_path: str) -> Optional[str]:
        """Get content of a file from cache."""
        return self.content_cache.get(file_path)
    
    def get_symbols_in_file(self, file_path: str) -> list[CodeSymbol]:
        """Get all symbols defined in a file."""
        return [
            symbol for symbol in self.symbol_graph.values()
            if symbol.file_path == file_path
        ]


# Global instance
_rag_context: Optional[EnhancedRAGContext] = None


def get_enhanced_rag_context(project_root: Optional[Path] = None) -> EnhancedRAGContext:
    """Get or create enhanced RAG context instance."""
    global _rag_context
    if _rag_context is None:
        if project_root is None:
            from pathlib import Path
            project_root = Path.cwd()
        _rag_context = EnhancedRAGContext(project_root)
    return _rag_context
