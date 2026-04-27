"""
Project tools service for executing operations on project files
"""
from typing import Dict, Any, Optional, List
from pathlib import Path
import os
import re
from app.services.project_analyzer import ProjectAnalyzer, FileType

class ProjectTools:
    """Tools for interacting with project files and structure"""
    
    def __init__(self, project_root: Optional[str] = None):
        self.analyzer = ProjectAnalyzer(project_root)
        self.project_root = self.analyzer.project_root
    
    def count_files(self, folder: Optional[str] = None) -> Dict[str, Any]:
        """Count files in a folder"""
        try:
            files = self.analyzer.list_files(folder, limit=10000)
            return {
                'success': True,
                'folder': folder or 'root',
                'count': len(files),
                'by_type': self.analyzer._count_file_types(files)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def list_project_files(self, folder: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
        """List files in project"""
        try:
            files = self.analyzer.list_files(folder, limit=limit)
            return {
                'success': True,
                'folder': folder or 'root',
                'count': len(files),
                'files': [
                    {
                        'path': f.path,
                        'name': f.name,
                        'size': f.size,
                        'type': f.type.value,
                        'extension': f.extension
                    }
                    for f in files
                ]
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def list_project_structure(self, folder: Optional[str] = None) -> Dict[str, Any]:
        """Get project folder structure"""
        try:
            folders = self.analyzer.list_folders(folder, limit=100)
            return {
                'success': True,
                'folder': folder or 'root',
                'count': len(folders),
                'folders': [
                    {
                        'path': f.path,
                        'name': f.name,
                        'files': f.file_count,
                        'subfolders': f.folder_count,
                        'size': f.size
                    }
                    for f in folders
                ]
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def search_in_project(self, pattern: str, file_type: Optional[str] = None) -> Dict[str, Any]:
        """Search for files in project"""
        try:
            files = self.analyzer.search_files(pattern, file_type)
            return {
                'success': True,
                'pattern': pattern,
                'count': len(files),
                'results': [
                    {
                        'path': f.path,
                        'name': f.name,
                        'type': f.type.value
                    }
                    for f in files
                ]
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def read_file(self, file_path: str) -> Dict[str, Any]:
        """Read file content"""
        result = self.analyzer.read_file(file_path)
        if result and 'content' in result:
            return {
                'success': True,
                'path': file_path,
                'content': result.get('content', ''),
                'type': result.get('type', 'unknown'),
                'size': result.get('size', 0)
            }
        return result or {'success': False, 'error': 'Unknown error'}
    
    def read_file_snippet(self, file_path: str, start_line: int = 1, end_line: Optional[int] = None) -> Dict[str, Any]:
        """Read specific lines from a file"""
        try:
            result = self.analyzer.read_file(file_path)
            
            if not result or 'error' in result:
                return result or {'success': False, 'error': 'Unknown error'}
            
            if result.get('type') == 'binary':
                return {'success': False, 'error': 'Cannot read binary file'}
            
            content = result.get('content', '')
            lines = content.split('\n')
            
            start_idx = max(0, start_line - 1)
            end_idx = min(len(lines), (end_line or len(lines)))
            
            snippet_lines = lines[start_idx:end_idx]
            
            return {
                'success': True,
                'path': file_path,
                'start_line': start_line,
                'end_line': end_idx,
                'total_lines': len(lines),
                'content': '\n'.join(snippet_lines)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def write_file(self, file_path: str, content: str, create_if_missing: bool = True) -> Dict[str, Any]:
        """Write content to file"""
        try:
            full_path = self.project_root / file_path
            
            # Security: Prevent path traversal
            if not str(full_path).startswith(str(self.project_root)):
                return {'success': False, 'error': 'Path traversal not allowed'}
            
            if full_path.exists() and full_path.is_dir():
                return {'success': False, 'error': 'Path is a directory'}
            
            if not create_if_missing and not full_path.exists():
                return {'success': False, 'error': 'File does not exist'}
            
            # Create parent directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write content
            full_path.write_text(content, encoding='utf-8')
            
            return {
                'success': True,
                'path': file_path,
                'size': len(content),
                'message': f'Successfully wrote {len(content)} bytes'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def append_to_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """Append content to file"""
        try:
            full_path = self.project_root / file_path
            
            # Security: Prevent path traversal
            if not str(full_path).startswith(str(self.project_root)):
                return {'success': False, 'error': 'Path traversal not allowed'}
            
            if not full_path.exists():
                return {'success': False, 'error': 'File does not exist'}
            
            if full_path.is_dir():
                return {'success': False, 'error': 'Path is a directory'}
            
            # Append content
            existing = full_path.read_text(encoding='utf-8')
            full_path.write_text(existing + content, encoding='utf-8')
            
            return {
                'success': True,
                'path': file_path,
                'appended_bytes': len(content),
                'message': f'Successfully appended {len(content)} bytes'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def search_file_content(self, pattern: str, file_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """Search for pattern in file contents"""
        try:
            files = self.analyzer.list_files(limit=1000)
            results = []
            
            # Filter by type if specified
            if file_types:
                files = [f for f in files if f.type.value in file_types]
            
            for file_info in files:
                try:
                    content_result = self.analyzer.read_file(file_info.path)
                    if content_result and 'content' in content_result and content_result['content']:
                        content = content_result['content']
                        
                        # Find all matches
                        matches = []
                        for i, line in enumerate(content.split('\n'), 1):
                            if re.search(pattern, line, re.IGNORECASE):
                                matches.append({
                                    'line': i,
                                    'text': line.strip()
                                })
                        
                        if matches:
                            results.append({
                                'file': file_info.path,
                                'type': file_info.type.value,
                                'matches': matches[:5]  # Limit to 5 matches per file
                            })
                except Exception:
                    continue
            
            return {
                'success': True,
                'pattern': pattern,
                'files_found': len(results),
                'results': results[:10]  # Limit to 10 files
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def create_file(self, file_path: str, content: str = '') -> Dict[str, Any]:
        """Create a new file"""
        try:
            full_path = self.project_root / file_path
            
            # Security: Prevent path traversal
            if not str(full_path).startswith(str(self.project_root)):
                return {'success': False, 'error': 'Path traversal not allowed'}
            
            if full_path.exists():
                return {'success': False, 'error': 'File already exists'}
            
            # Create parent directories
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create file
            full_path.write_text(content, encoding='utf-8')
            
            return {
                'success': True,
                'path': file_path,
                'message': 'File created successfully'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_project_info(self) -> Dict[str, Any]:
        """Get comprehensive project information"""
        try:
            metadata = self.analyzer.get_project_metadata()
            stats = self.analyzer.get_file_statistics()
            
            return {
                'success': True,
                'project': {
                    'root': str(self.project_root),
                    'metadata': metadata,
                    'statistics': stats
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
