"""
Semantic Code Search Service

Provides intelligent code search using:
- Keyword extraction
- Function/class name matching
- Import analysis
- Context-aware ranking
- Code pattern matching
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CodeSearchResult:
    """Result from a code search."""
    file_path: str
    line_number: int
    content: str
    match_type: str  # "function", "class", "import", "keyword", "pattern"
    relevance_score: float
    context: str = ""
    language: str = ""


class SemanticCodeSearch:
    """
    Semantic code search that understands code context.
    
    Unlike simple grep, this search:
    - Understands function/class definitions
    - Matches imports and dependencies
    - Ranks results by relevance
    - Provides context around matches
    """

    # Language detection patterns
    LANGUAGE_PATTERNS = {
        "python": [r"\.py$", r"def\s+\w+", r"import\s+\w+", r"class\s+\w+"],
        "javascript": [r"\.jsx?$", r"function\s+\w+", r"const\s+\w+\s*=", r"import\s+.*\s+from"],
        "typescript": [r"\.tsx?$", r"interface\s+\w+", r"type\s+\w+\s*=", r":\s*(string|number|boolean)"],
        "java": [r"\.java$", r"public\s+class", r"private\s+\w+", r"void\s+\w+"],
        "go": [r"\.go$", r"func\s+\w+", r"package\s+\w+", r"import\s+\("],
        "rust": [r"\.rs$", r"fn\s+\w+", r"let\s+mut", r"impl\s+\w+"],
    }

    # Code element patterns
    CODE_PATTERNS = {
        "function": r"(?:def|function|func|fn)\s+(\w+)",
        "class": r"(?:class|interface|type|struct)\s+(\w+)",
        "import": r"(?:import|from|require)\s+['\"]?([\w./-]+)['\"]?",
        "variable": r"(?:const|let|var|val)\s+(\w+)",
        "method": r"(?:def|function|func|fn)\s+(\w+)\s*\(",
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.index: List[Dict[str, Any]] = []
        self._indexed = False

    def index_project(self) -> int:
        """Index all code files in the project."""
        self.index = []
        files_indexed = 0

        ignore_dirs = {
            ".git", "node_modules", "__pycache__", ".venv", "venv",
            ".idea", ".vscode", "dist", "build", "target", ".cache",
        }

        for file_path in self.project_root.rglob("*"):
            # Skip directories and ignored dirs
            if not file_path.is_file():
                continue
            if any(part in ignore_dirs for part in file_path.parts):
                continue

            # Only index text files
            if not self._is_code_file(file_path):
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                language = self._detect_language(file_path, content)
                
                # Extract code elements
                elements = self._extract_code_elements(content, language)
                
                # Add to index
                for element in elements:
                    self.index.append({
                        "file": str(file_path.relative_to(self.project_root)),
                        "line": element["line"],
                        "content": element["content"],
                        "type": element["type"],
                        "name": element.get("name", ""),
                        "language": language,
                        "context": element.get("context", ""),
                    })
                
                files_indexed += 1
            except Exception:
                continue

        self._indexed = True
        return files_indexed

    def search(self, query: str, limit: int = 20) -> Dict[str, Any]:
        """
        Search code semantically.
        
        Understands:
        - Function/class names
        - Keywords and concepts
        - Import patterns
        - Code patterns
        """
        if not self._indexed:
            self.index_project()

        query_lower = query.lower()
        query_terms = set(query_lower.split())
        
        results = []
        
        for item in self.index:
            score = 0.0
            match_type = "keyword"
            
            content_lower = item["content"].lower()
            name_lower = item.get("name", "").lower()
            
            # Exact name match (highest priority)
            if query_lower == name_lower:
                score += 10.0
                match_type = item["type"]
            
            # Name contains query
            elif query_lower in name_lower:
                score += 5.0
                match_type = item["type"]
            
            # Content contains query
            elif query_lower in content_lower:
                score += 3.0
                match_type = "keyword"
            
            # Term matching
            else:
                matching_terms = query_terms & set(content_lower.split())
                if matching_terms:
                    score += len(matching_terms) * 1.0
                    match_type = "keyword"
            
            # Boost for function/class definitions
            if item["type"] in ("function", "class") and score > 0:
                score *= 1.5
            
            # Boost for imports
            if item["type"] == "import" and score > 0:
                score *= 1.2
            
            if score > 0:
                results.append({
                    "file_path": item["file"],
                    "line_number": item["line"],
                    "content": item["content"],
                    "match_type": match_type,
                    "relevance_score": round(score, 2),
                    "context": item.get("context", ""),
                    "language": item.get("language", ""),
                })
        
        # Sort by relevance score
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return {
            "success": True,
            "query": query,
            "total_results": len(results),
            "results": results[:limit],
        }

    def _extract_code_elements(self, content: str, language: str) -> List[Dict]:
        """Extract functions, classes, imports, etc. from code."""
        elements = []
        lines = content.split("\n")
        
        for line_num, line in enumerate(lines, 1):
            # Function definitions
            func_match = re.search(self.CODE_PATTERNS["function"], line)
            if func_match:
                elements.append({
                    "line": line_num,
                    "content": line.strip(),
                    "type": "function",
                    "name": func_match.group(1),
                    "context": self._get_context(lines, line_num, 2),
                })
            
            # Class definitions
            class_match = re.search(self.CODE_PATTERNS["class"], line)
            if class_match:
                elements.append({
                    "line": line_num,
                    "content": line.strip(),
                    "type": "class",
                    "name": class_match.group(1),
                    "context": self._get_context(lines, line_num, 2),
                })
            
            # Imports
            import_match = re.search(self.CODE_PATTERNS["import"], line)
            if import_match:
                elements.append({
                    "line": line_num,
                    "content": line.strip(),
                    "type": "import",
                    "name": import_match.group(1),
                    "context": "",
                })
        
        return elements

    def _get_context(self, lines: List[str], line_num: int, context_lines: int) -> str:
        """Get surrounding context for a line."""
        start = max(0, line_num - context_lines - 1)
        end = min(len(lines), line_num + context_lines)
        return "\n".join(lines[start:end])

    def _detect_language(self, file_path: Path, content: str) -> str:
        """Detect programming language."""
        # Check extension first
        ext = file_path.suffix.lower()
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".java": "java",
            ".go": "go",
            ".rs": "rust",
        }
        if ext in ext_map:
            return ext_map[ext]
        
        # Check content patterns
        for lang, patterns in self.LANGUAGE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content):
                    return lang
        
        return "unknown"

    def _is_code_file(self, file_path: Path) -> bool:
        """Check if file is a code file."""
        code_extensions = {
            ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs",
            ".rb", ".php", ".cs", ".cpp", ".c", ".h", ".hpp",
            ".css", ".scss", ".html", ".json", ".yaml", ".yml", ".md",
            ".sh", ".bash", ".zsh",
        }
        return file_path.suffix.lower() in code_extensions


# Global instance
_search_service: Optional[SemanticCodeSearch] = None


def get_semantic_search(project_root: Optional[Path] = None) -> SemanticCodeSearch:
    """Get or create semantic search instance."""
    global _search_service
    if _search_service is None:
        if project_root is None:
            project_root = Path.cwd()
        _search_service = SemanticCodeSearch(project_root)
    return _search_service
