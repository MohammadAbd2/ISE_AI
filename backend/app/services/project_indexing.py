"""
Project Indexing Service - Automatically indexes opened project structure
Provides fast access to file counts, directory structure, and file metadata
"""
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import os
import fnmatch


@dataclass
class ProjectIndex:
    """Complete project index data"""
    root_path: str
    total_files: int = 0
    total_dirs: int = 0
    files_by_category: Dict[str, int] = field(default_factory=dict)
    files_by_extension: Dict[str, int] = field(default_factory=dict)
    directory_structure: Dict[str, int] = field(default_factory=dict)  # dir_path -> file_count
    file_list: List[str] = field(default_factory=list)
    indexed_at: str = ""


class ProjectIndexingService:
    """
    Service for indexing and querying project structure.
    Runs on project open and provides fast filesystem queries.
    """

    # Default ignore patterns
    IGNORE_PATTERNS = {
        ".git", ".gitignore", "__pycache__", ".pytest_cache", "node_modules",
        ".venv", "venv", ".env", ".idea", ".vscode", "dist", "build",
        "target", ".gradle", ".DS_Store", "Thumbs.db", ".lock",
        "package-lock.json", "yarn.lock", "pnpm-lock.yaml", ".next", "out",
        ".cache", ".pytest", ".tox", ".eggs", ".mypy_cache", ".egg-info",
        "*.pyc", "*.pyo", "*.class", "*.o", "*.so", ".coverage"
    }

    def __init__(self):
        self.current_index: Optional[ProjectIndex] = None
        self.is_indexing = False

    def index_project(self, root_path: str) -> ProjectIndex:
        """
        Index the entire project structure.
        This should be called when a project is opened.
        """
        self.is_indexing = True
        root = Path(root_path)
        
        if not root.exists():
            raise ValueError(f"Project root does not exist: {root_path}")

        index = ProjectIndex(
            root_path=str(root.resolve()),
            indexed_at=datetime.now().isoformat()
        )

        # Walk the directory tree
        for item in root.rglob("*"):
            if self._should_ignore(item):
                continue

            if item.is_file():
                index.total_files += 1
                index.file_list.append(str(item.relative_to(root)))
                
                # Count by extension
                ext = item.suffix.lower() or "no_extension"
                index.files_by_extension[ext] = index.files_by_extension.get(ext, 0) + 1

                # Count by category
                category = self._categorize_file(item)
                index.files_by_category[category] = index.files_by_category.get(category, 0) + 1

                # Count files in parent directory
                parent = str(item.parent.relative_to(root))
                index.directory_structure[parent] = index.directory_structure.get(parent, 0) + 1

            elif item.is_dir():
                index.total_dirs += 1
                # Ensure directory is in structure even if empty
                dir_path = str(item.relative_to(root))
                if dir_path not in index.directory_structure:
                    index.directory_structure[dir_path] = 0

        self.current_index = index
        self.is_indexing = False
        return index

    def count_files_in_folder(self, folder_path: str) -> Dict[str, Any]:
        """
        Count files in a specific folder within the project.
        Uses the index for fast queries.
        """
        if not self.current_index:
            return {"success": False, "error": "Project not indexed"}

        # Normalize folder path
        folder = folder_path.strip("/").strip("\\")
        
        # If folder is empty or ".", count all files
        if not folder or folder in [".", "./"]:
            return {
                "success": True,
                "folder": "root",
                "total_files": self.current_index.total_files,
                "by_category": self.current_index.files_by_category,
                "by_extension": self.current_index.files_by_extension,
            }

        # Count files in the specific folder
        file_count = 0
        category_counts = {}
        extension_counts = {}
        
        # Check if folder exists in index
        folder_found = False
        for file_path in self.current_index.file_list:
            # Check if file is in this folder or subfolder
            if file_path.startswith(folder + "/") or file_path.startswith(folder + "\\"):
                folder_found = True
                file_count += 1
                
                # Get the immediate parent for categorization
                parts = file_path.split("/")
                if len(parts) > 1:
                    # Get file extension
                    ext = Path(file_path).suffix.lower() or "no_extension"
                    extension_counts[ext] = extension_counts.get(ext, 0) + 1
                    
                    # Categorize
                    category = self._categorize_file(Path(self.current_index.root_path) / file_path)
                    category_counts[category] = category_counts.get(category, 0) + 1

        if not folder_found:
            # Try to scan the folder directly from filesystem
            try:
                return self._scan_folder_direct(folder)
            except Exception as e:
                return {"success": False, "error": f"Folder '{folder}' not found in project index"}

        return {
            "success": True,
            "folder": folder,
            "total_files": file_count,
            "by_category": category_counts,
            "by_extension": extension_counts,
        }

    def list_files_in_folder(self, folder_path: str, limit: int = 50) -> Dict[str, Any]:
        """
        List files in a specific folder within the project.
        """
        if not self.current_index:
            return {"success": False, "error": "Project not indexed"}

        folder = folder_path.strip("/").strip("\\")
        files = []
        
        for file_path in self.current_index.file_list:
            # Check if file is in this folder
            if file_path.startswith(folder + "/") or file_path.startswith(folder + "\\"):
                # Get just the filename
                filename = file_path.split("/")[-1].split("\\")[-1]
                files.append({
                    "path": file_path,
                    "name": filename,
                })
                
                if len(files) >= limit:
                    break

        return {
            "success": True,
            "folder": folder,
            "count": len(files),
            "files": files,
        }

    def get_project_structure(self) -> Dict[str, Any]:
        """
        Get the complete project structure summary.
        """
        if not self.current_index:
            return {"success": False, "error": "Project not indexed"}

        return {
            "success": True,
            "root": self.current_index.root_path,
            "total_files": self.current_index.total_files,
            "total_dirs": self.current_index.total_dirs,
            "by_category": self.current_index.files_by_category,
            "by_extension": self.current_index.files_by_extension,
            "indexed_at": self.current_index.indexed_at,
        }

    def _scan_folder_direct(self, folder_path: str) -> Dict[str, Any]:
        """
        Direct filesystem scan for folders not in the index.
        Fallback method when folder is not in cached index.
        """
        if not self.current_index:
            raise ValueError("Project not indexed")

        root = Path(self.current_index.root_path)
        target = root / folder_path
        
        if not target.exists():
            raise ValueError(f"Folder not found: {folder_path}")

        file_count = 0
        category_counts = {}
        extension_counts = {}

        for item in target.glob("*"):
            if self._should_ignore(item) or not item.is_file():
                continue

            file_count += 1
            ext = item.suffix.lower() or "no_extension"
            extension_counts[ext] = extension_counts.get(ext, 0) + 1
            category = self._categorize_file(item)
            category_counts[category] = category_counts.get(category, 0) + 1

        return {
            "success": True,
            "folder": folder_path,
            "total_files": file_count,
            "by_category": category_counts,
            "by_extension": extension_counts,
        }

    def _should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored"""
        for part in path.parts:
            if part in self.IGNORE_PATTERNS or part.startswith("."):
                return True
        
        name = path.name
        for pattern in self.IGNORE_PATTERNS:
            if fnmatch.fnmatch(name, pattern):
                return True
        
        return False

    def _categorize_file(self, path: Path) -> str:
        """Categorize a file based on extension and location"""
        name_lower = path.name.lower()
        ext = path.suffix.lower()

        # Check if test file
        test_patterns = ["test", "spec", "_test.py", ".test.js", ".spec.ts", "tests/"]
        if any(test_pattern in str(path).lower() for test_pattern in test_patterns):
            return "test"

        # Categorize by extension
        source_code_exts = {".py", ".ts", ".tsx", ".js", ".jsx", ".java", ".kt", ".rs", ".go", ".cpp", ".cc", ".h", ".cs", ".rb", ".php", ".swift"}
        config_exts = {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf"}
        build_exts = {".sh", ".gradle", ".maven", ".make", ".bat", ".ps1"}
        doc_exts = {".md", ".rst", ".txt", ".adoc", ".tex"}

        if ext in source_code_exts:
            return "source_code"
        elif ext in config_exts:
            return "config"
        elif ext in build_exts:
            return "build"
        elif ext in doc_exts:
            return "documentation"
        elif ext in {".jpg", ".png", ".gif", ".svg", ".ico", ".webp", ".mp3", ".mp4"}:
            return "asset"
        elif ext in {".csv", ".db", ".sqlite", ".parquet", ".pkl"}:
            return "data"
        elif ext in {".zip", ".tar", ".gz", ".rar", ".7z"}:
            return "archive"
        
        return "other"


# Global instance
_indexing_service: Optional[ProjectIndexingService] = None


def get_project_indexer() -> ProjectIndexingService:
    """Get or create the global project indexing service"""
    global _indexing_service
    if _indexing_service is None:
        _indexing_service = ProjectIndexingService()
    return _indexing_service


def index_project(root_path: str) -> ProjectIndex:
    """Convenience function to index a project"""
    indexer = get_project_indexer()
    return indexer.index_project(root_path)
