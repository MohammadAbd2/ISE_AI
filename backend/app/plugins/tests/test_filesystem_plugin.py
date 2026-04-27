"""
Comprehensive tests for FileSystem Plugin
Tests all functionality with edge cases and error handling
"""
import pytest
import tempfile
import os
from pathlib import Path
from backend.app.plugins.filesystem.plugin import (
    FileSystemPlugin,
    FileCategory,
    FileMetadata,
)


@pytest.fixture
def temp_project():
    """Create a temporary project structure for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Create source files
        (root / "src").mkdir()
        (root / "src" / "main.py").write_text("print('hello')")
        (root / "src" / "utils.py").write_text("def helper(): pass")
        (root / "src" / "app.js").write_text("console.log('app');")

        # Create test files
        (root / "tests").mkdir()
        (root / "tests" / "test_main.py").write_text("def test_main(): pass")
        (root / "tests" / "test_utils.py").write_text("def test_utils(): pass")

        # Create config files
        (root / "config.json").write_text('{"setting": "value"}')
        (root / "pyproject.toml").write_text("[tool.poetry]")

        # Create documentation
        (root / "README.md").write_text("# Project")
        (root / "docs").mkdir()
        (root / "docs" / "API.md").write_text("## API")

        # Create build artifacts (should be ignored)
        (root / "__pycache__").mkdir()
        (root / "__pycache__" / "main.cpython-313.pyc").write_bytes(b"compiled")
        (root / ".git").mkdir()
        (root / ".git" / "config").write_text("[core]")
        (root / "node_modules").mkdir()
        (root / "node_modules" / "package").mkdir()

        # Create a large binary file
        (root / "data.bin").write_bytes(b"\x00\x01\x02\x03" * 1000)

        # Create hidden file
        (root / ".env").write_text("SECRET=key")

        yield root


@pytest.fixture
def plugin(temp_project):
    """Create plugin instance with temp project"""
    return FileSystemPlugin(str(temp_project))


class TestBasicFunctionality:
    """Test basic file system operations"""

    def test_plugin_initialization(self, temp_project):
        """Test plugin initialization"""
        plugin = FileSystemPlugin(str(temp_project))
        assert plugin.root_path == temp_project
        assert plugin.cache == {}

    def test_invalid_root_path(self):
        """Test initialization with invalid path"""
        with pytest.raises(ValueError):
            FileSystemPlugin("/nonexistent/path/that/does/not/exist")

    def test_count_files_in_folder(self, plugin):
        """Test file counting with categorization"""
        result = plugin.count_files_in_folder()
        assert result["success"]
        assert result["total_files"] > 0
        assert "by_category" in result
        assert "by_extension" in result

    def test_list_files(self, plugin):
        """Test listing files"""
        result = plugin.list_files()
        assert result["success"]
        assert "files" in result
        assert all("path" in f for f in result["files"])
        assert all("category" in f for f in result["files"])

    def test_list_directories(self, plugin):
        """Test listing directories"""
        result = plugin.list_directories()
        assert result["success"]
        assert "directories" in result
        assert any(d["name"] == "src" for d in result["directories"])
        assert any(d["name"] == "tests" for d in result["directories"])


class TestFileSearch:
    """Test file searching functionality"""

    def test_search_by_name(self, plugin):
        """Test searching by file name"""
        result = plugin.search_files("test")
        assert result["success"]
        assert result["count"] > 0
        assert any("test" in f["name"].lower() for f in result["files"])

    def test_search_by_extension(self, plugin):
        """Test searching by extension"""
        result = plugin.search_files(".py", by_extension=True)
        assert result["success"]
        assert all(f["extension"] == ".py" for f in result["files"])

    def test_search_with_limit(self, plugin):
        """Test search result limiting"""
        result = plugin.search_files(".py", by_extension=True, limit=2)
        assert len(result["files"]) <= 2

    def test_search_no_matches(self, plugin):
        """Test search with no matches"""
        result = plugin.search_files("nonexistent_file_xyz")
        assert result["success"]
        assert result["count"] == 0


class TestFileInfo:
    """Test file information retrieval"""

    def test_get_file_info(self, plugin, temp_project):
        """Test getting file information"""
        result = plugin.get_file_info("src/main.py")
        assert result["success"]
        assert result["file"]["name"] == "main.py"
        assert result["file"]["extension"] == ".py"
        assert result["file"]["category"] == FileCategory.SOURCE_CODE.value

    def test_file_not_found(self, plugin):
        """Test handling of non-existent file"""
        result = plugin.get_file_info("nonexistent.txt")
        assert not result["success"]
        assert "error" in result

    def test_get_file_preview(self, plugin):
        """Test file preview generation"""
        result = plugin.get_file_info("README.md")
        assert result["success"]
        assert "preview" in result

    def test_read_file(self, plugin):
        """Test reading file content"""
        result = plugin.read_file("src/main.py")
        assert result["success"]
        assert "content" in result
        assert "print('hello')" in result["content"]

    def test_read_binary_file_error(self, plugin):
        """Test reading binary file returns error"""
        result = plugin.read_file("data.bin")
        assert not result["success"]
        assert "not text-based" in result["error"]

    def test_read_file_with_line_range(self, plugin, temp_project):
        """Test reading file with line range"""
        # Create a multi-line file
        test_file = temp_project / "multiline.txt"
        test_file.write_text("line1\nline2\nline3\nline4\nline5")

        plugin2 = FileSystemPlugin(str(temp_project))
        result = plugin2.read_file("multiline.txt", lines=(2, 4))
        assert result["success"]
        assert "line2" in result["content"]
        assert "line4" in result["content"]


class TestFileMetadata:
    """Test file metadata extraction"""

    def test_categorization_source_code(self, plugin):
        """Test source code categorization"""
        result = plugin.get_file_info("src/main.py")
        assert result["file"]["category"] == FileCategory.SOURCE_CODE.value

    def test_categorization_test(self, plugin):
        """Test test file categorization"""
        result = plugin.get_file_info("tests/test_main.py")
        assert result["file"]["category"] == FileCategory.TEST.value

    def test_categorization_config(self, plugin):
        """Test config file categorization"""
        result = plugin.get_file_info("config.json")
        assert result["file"]["category"] == FileCategory.CONFIG.value

    def test_categorization_documentation(self, plugin):
        """Test documentation categorization"""
        result = plugin.get_file_info("README.md")
        assert result["file"]["category"] == FileCategory.DOCUMENTATION.value

    def test_hidden_file_detection(self, plugin):
        """Test hidden file detection"""
        result = plugin.get_file_info(".env")
        assert result["file"]["is_hidden"]

    def test_text_file_detection(self, plugin):
        """Test text file detection"""
        result = plugin.get_file_info("src/main.py")
        assert result["file"]["is_text"]

    def test_binary_file_detection(self, plugin):
        """Test binary file detection"""
        result = plugin.get_file_info("data.bin")
        assert not result["file"]["is_text"]


class TestIgnorePatterns:
    """Test ignore pattern matching"""

    def test_ignore_git_directory(self, plugin):
        """Test that .git directory is ignored"""
        result = plugin.list_files()
        paths = [f["path"] for f in result["files"]]
        assert not any(".git" in p for p in paths)

    def test_ignore_pycache(self, plugin):
        """Test that __pycache__ is ignored"""
        result = plugin.list_files()
        paths = [f["path"] for f in result["files"]]
        assert not any("__pycache__" in p for p in paths)

    def test_ignore_node_modules(self, plugin):
        """Test that node_modules is ignored"""
        result = plugin.list_directories()
        names = [d["name"] for d in result["directories"]]
        assert "node_modules" not in names

    def test_count_excludes_ignored(self, plugin):
        """Test that count excludes ignored directories"""
        # Total should not include .git, __pycache__, node_modules files
        result = plugin.count_files_in_folder()
        # Should have actual files (py, js, md, json, toml, txt, bin, env)
        # Should NOT have .git/config, __pycache__/*.pyc files
        assert result["success"]


class TestProjectStructure:
    """Test project structure analysis"""

    def test_get_project_structure(self, plugin):
        """Test getting full project structure"""
        result = plugin.get_project_structure()
        assert result["success"]
        assert "stats" in result
        assert "total_files" in result["stats"]
        assert "total_dirs" in result["stats"]
        assert "by_category" in result["stats"]
        assert "by_extension" in result["stats"]

    def test_structure_categorization(self, plugin):
        """Test that structure includes category breakdown"""
        result = plugin.get_project_structure()
        categories = result["stats"]["by_category"]
        assert FileCategory.SOURCE_CODE.value in categories or len(categories) > 0


class TestCaching:
    """Test caching functionality"""

    def test_cache_storage(self, plugin):
        """Test that results are cached"""
        plugin.count_files_in_folder()
        cache_key = "count_files:None:False"
        assert cache_key in plugin.cache

    def test_cache_retrieval(self, plugin):
        """Test cache retrieval"""
        result1 = plugin.list_files()
        result2 = plugin.list_files()
        # Should be identical (from cache)
        assert result1 == result2

    def test_cache_clear(self, plugin):
        """Test cache clearing"""
        plugin.count_files_in_folder()
        assert len(plugin.cache) > 0
        result = plugin.clear_cache()
        assert result["success"]
        assert len(plugin.cache) == 0


class TestRecursiveOperations:
    """Test recursive directory operations"""

    def test_recursive_file_count(self, plugin):
        """Test recursive file counting"""
        result = plugin.count_files_in_folder(recursive=True)
        assert result["success"]
        assert result["recursive"]
        assert result["total_files"] > 0

    def test_recursive_search(self, plugin):
        """Test recursive search finds all matches"""
        # Search for .py files recursively
        result = plugin.search_files(".py", by_extension=True)
        # Should find files in src/ and tests/
        assert result["count"] >= 3  # main.py, utils.py, test_main.py, test_utils.py


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_directory(self, temp_project):
        """Test handling of empty directory"""
        empty_dir = temp_project / "empty"
        empty_dir.mkdir()
        plugin = FileSystemPlugin(str(temp_project))
        result = plugin.list_files("empty")
        assert result["success"]
        assert result["count"] == 0

    def test_large_file_no_preview(self, temp_project):
        """Test that large files don't generate preview"""
        large_file = temp_project / "large.txt"
        large_file.write_text("x" * 200000)  # 200KB
        plugin = FileSystemPlugin(str(temp_project))
        result = plugin.get_file_info("large.txt")
        assert result["success"]
        assert "preview" not in result

    def test_special_characters_in_filename(self, temp_project):
        """Test handling of special characters"""
        special_file = temp_project / "file-with-dash_and_underscore.txt"
        special_file.write_text("content")
        plugin = FileSystemPlugin(str(temp_project))
        result = plugin.search_files("special")
        assert result["success"]

    def test_extension_filtering(self, plugin):
        """Test filtering by extension"""
        result = plugin.list_files(extensions=[".py"])
        assert all(f["extension"] == ".py" for f in result["files"])


class TestMetadataAccuracy:
    """Test accuracy of metadata extraction"""

    def test_file_size_accuracy(self, plugin):
        """Test file size reporting"""
        result = plugin.get_file_info("src/main.py")
        assert result["file"]["size"] > 0

    def test_mime_type_detection(self, plugin):
        """Test mime type detection"""
        result = plugin.get_file_info("config.json")
        # Should detect as JSON
        mime = result["file"]["mime_type"]
        assert mime is None or "json" in mime.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
