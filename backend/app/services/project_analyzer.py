"""
Project analysis service for understanding project structure and content
"""
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum
import mimetypes

class FileType(Enum):
    """File type classification"""
    PYTHON = "python"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    JAVA = "java"
    KOTLIN = "kotlin"
    RUST = "rust"
    GO = "go"
    CPP = "cpp"
    CSHARP = "csharp"
    HTML = "html"
    CSS = "css"
    JSON = "json"
    YAML = "yaml"
    XML = "xml"
    MARKDOWN = "markdown"
    TEXT = "text"
    BINARY = "binary"
    UNKNOWN = "unknown"

@dataclass
class FileInfo:
    """Information about a single file"""
    path: str  # Relative path from project root
    name: str
    size: int
    type: FileType
    extension: str
    is_test: bool = False
    is_generated: bool = False

@dataclass
class FolderInfo:
    """Information about a folder"""
    path: str  # Relative path
    name: str
    file_count: int
    folder_count: int
    size: int

class ProjectAnalyzer:
    """Analyzes project structure and content"""
    
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root or os.getcwd())
        self.cache: Dict[str, Any] = {}
        self.ignore_patterns = self._get_ignore_patterns()
    
    def _get_ignore_patterns(self) -> Set[str]:
        """Get patterns to ignore when analyzing project"""
        return {
            '.git', '.gitignore', '__pycache__', '.pytest_cache', 'node_modules',
            '.venv', 'venv', '.env', '*.pyc', '.idea', '.vscode', 'dist', 'build',
            'target', '.gradle', '.DS_Store', 'Thumbs.db', '.lock', 'package-lock.json',
            'yarn.lock', 'pnpm-lock.yaml', '.next', 'out', '.cache'
        }
    
    def should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored"""
        for part in path.parts:
            if part in self.ignore_patterns or part.startswith('.'):
                return True
            # Check for compiled/generated files
            if part.endswith('.pyc') or part.endswith('.o') or part.endswith('.class'):
                return True
        return False
    
    def get_file_type(self, file_path: Path) -> FileType:
        """Determine file type from extension"""
        ext = file_path.suffix.lower()
        
        type_map = {
            '.py': FileType.PYTHON,
            '.ts': FileType.TYPESCRIPT,
            '.tsx': FileType.TYPESCRIPT,
            '.js': FileType.JAVASCRIPT,
            '.jsx': FileType.JAVASCRIPT,
            '.java': FileType.JAVA,
            '.kt': FileType.KOTLIN,
            '.rs': FileType.RUST,
            '.go': FileType.GO,
            '.cpp': FileType.CPP,
            '.cc': FileType.CPP,
            '.cxx': FileType.CPP,
            '.h': FileType.CPP,
            '.cs': FileType.CSHARP,
            '.html': FileType.HTML,
            '.css': FileType.CSS,
            '.json': FileType.JSON,
            '.yaml': FileType.YAML,
            '.yml': FileType.YAML,
            '.xml': FileType.XML,
            '.md': FileType.MARKDOWN,
            '.txt': FileType.TEXT,
        }
        
        return type_map.get(ext, FileType.UNKNOWN)
    
    def get_project_metadata(self) -> Dict[str, Any]:
        """Get comprehensive project metadata"""
        if 'metadata' in self.cache:
            return self.cache['metadata']
        
        try:
            files = self.list_files()
            folders = self.list_folders()
            
            metadata = {
                'root': str(self.project_root),
                'total_files': len(files),
                'total_folders': len(folders),
                'file_types': self._count_file_types(files),
                'size_mb': sum(f.size for f in files) / (1024 * 1024),
                'primary_language': self._detect_primary_language(files),
                'framework': self._detect_framework(),
                'has_tests': any(f.is_test for f in files),
                'top_level_folders': [f.name for f in folders if '/' not in f.path],
            }
            
            self.cache['metadata'] = metadata
            return metadata
        except Exception as e:
            return {'error': str(e)}
    
    def list_files(self, folder: Optional[str] = None, limit: int = 1000) -> List[FileInfo]:
        """List files in project or subfolder"""
        start_path = self.project_root
        if folder:
            start_path = self.project_root / folder
        
        files = []
        count = 0
        
        try:
            for file_path in start_path.rglob('*'):
                if count >= limit:
                    break
                
                if not file_path.is_file() or self.should_ignore(file_path):
                    continue
                
                try:
                    rel_path = file_path.relative_to(self.project_root)
                    file_type = self.get_file_type(file_path)
                    size = file_path.stat().st_size
                    
                    files.append(FileInfo(
                        path=str(rel_path),
                        name=file_path.name,
                        size=size,
                        type=file_type,
                        extension=file_path.suffix,
                        is_test='test' in file_path.name or 'spec' in file_path.name,
                        is_generated='generated' in file_path.name.lower()
                    ))
                    count += 1
                except (OSError, ValueError):
                    continue
        except (OSError, TypeError):
            pass
        
        return sorted(files, key=lambda f: f.path)
    
    def list_folders(self, folder: Optional[str] = None, limit: int = 100) -> List[FolderInfo]:
        """List folders in project or subfolder"""
        start_path = self.project_root
        if folder:
            start_path = self.project_root / folder
        
        folders = []
        count = 0
        
        try:
            for folder_path in start_path.rglob('*'):
                if count >= limit:
                    break
                
                if not folder_path.is_dir() or self.should_ignore(folder_path):
                    continue
                
                try:
                    rel_path = folder_path.relative_to(self.project_root)
                    
                    # Count items
                    try:
                        items = list(folder_path.iterdir())
                        file_count = sum(1 for f in items if f.is_file())
                        folder_count = sum(1 for f in items if f.is_dir())
                        size = sum(f.stat().st_size for f in items if f.is_file())
                    except (OSError, TypeError):
                        file_count = folder_count = size = 0
                    
                    folders.append(FolderInfo(
                        path=str(rel_path),
                        name=folder_path.name,
                        file_count=file_count,
                        folder_count=folder_count,
                        size=size
                    ))
                    count += 1
                except (OSError, ValueError):
                    continue
        except (OSError, TypeError):
            pass
        
        return sorted(folders, key=lambda f: f.path)
    
    def read_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Read file content safely"""
        try:
            full_path = self.project_root / file_path
            
            # Security: Prevent path traversal
            if not str(full_path).startswith(str(self.project_root)):
                return {'error': 'Path traversal not allowed'}
            
            if not full_path.exists():
                return {'error': f'File not found: {file_path}'}
            
            if not full_path.is_file():
                return {'error': f'Not a file: {file_path}'}
            
            # Check file size (limit to 1MB for safety)
            size = full_path.stat().st_size
            if size > 1024 * 1024:
                return {'error': f'File too large: {size} bytes (max 1MB)'}
            
            # Try to read as text
            try:
                content = full_path.read_text(encoding='utf-8')
                return {
                    'path': file_path,
                    'content': content,
                    'size': size,
                    'type': self.get_file_type(full_path).value
                }
            except UnicodeDecodeError:
                return {
                    'path': file_path,
                    'content': None,
                    'size': size,
                    'type': 'binary',
                    'error': 'File is binary'
                }
        except Exception as e:
            return {'error': str(e)}
    
    def search_files(self, pattern: str, file_type: Optional[str] = None) -> List[FileInfo]:
        """Search for files matching pattern"""
        files = self.list_files()
        
        pattern_lower = pattern.lower()
        results = [f for f in files if pattern_lower in f.path.lower() or pattern_lower in f.name.lower()]
        
        if file_type:
            file_type_lower = file_type.lower()
            results = [f for f in results if f.type.value == file_type_lower]
        
        return results[:50]  # Limit results
    
    def get_file_statistics(self) -> Dict[str, Any]:
        """Get statistics about project files"""
        if 'stats' in self.cache:
            return self.cache['stats']
        
        files = self.list_files(limit=5000)
        
        stats = {
            'total_files': len(files),
            'total_size_mb': sum(f.size for f in files) / (1024 * 1024),
            'test_files': sum(1 for f in files if f.is_test),
            'by_type': {},
            'by_extension': {},
            'largest_files': sorted(files, key=lambda f: f.size, reverse=True)[:10]
        }
        
        for file_info in files:
            type_name = file_info.type.value
            stats['by_type'][type_name] = stats['by_type'].get(type_name, 0) + 1
            
            ext = file_info.extension or 'no_extension'
            stats['by_extension'][ext] = stats['by_extension'].get(ext, 0) + 1
        
        # Convert largest_files to serializable format
        stats['largest_files'] = [
            {'path': f.path, 'size_kb': round(f.size / 1024, 2)}
            for f in stats['largest_files']
        ]
        
        self.cache['stats'] = stats
        return stats
    
    def _count_file_types(self, files: List[FileInfo]) -> Dict[str, int]:
        """Count files by type"""
        counts = {}
        for file in files:
            type_name = file.type.value
            counts[type_name] = counts.get(type_name, 0) + 1
        return counts
    
    def _detect_primary_language(self, files: List[FileInfo]) -> str:
        """Detect primary programming language"""
        type_counts = self._count_file_types(files)
        
        # Weights for language detection
        weights = {
            FileType.PYTHON.value: 1.0,
            FileType.TYPESCRIPT.value: 1.2,
            FileType.JAVASCRIPT.value: 0.9,
            FileType.JAVA.value: 1.1,
            FileType.KOTLIN.value: 1.0,
            FileType.RUST.value: 1.3,
        }
        
        best_lang = None
        best_score = 0
        
        for lang, count in type_counts.items():
            weight = weights.get(lang, 0.5)
            score = count * weight
            if score > best_score:
                best_score = score
                best_lang = lang
        
        return best_lang or 'unknown'
    
    def _detect_framework(self) -> Optional[str]:
        """Detect project framework from files"""
        files = self.list_files(limit=200)
        file_names = {f.name.lower() for f in files}
        
        frameworks = {
            'django': {'manage.py', 'settings.py'},
            'flask': {'app.py', 'flask'},
            'fastapi': {'main.py', 'fastapi'},
            'react': {'package.json', 'react', 'src/app.jsx'},
            'vue': {'package.json', 'vue', 'vue.config.js'},
            'angular': {'package.json', 'angular', 'angular.json'},
            'spring': {'pom.xml', 'spring', 'application.properties'},
            'rails': {'gemfile', 'rails'},
            'express': {'package.json', 'express'},
            'nextjs': {'next.config.js', 'package.json'},
        }
        
        for framework, indicators in frameworks.items():
            if any(ind.lower() in file_names for ind in indicators):
                return framework
        
        return None
