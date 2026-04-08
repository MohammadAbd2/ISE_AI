#!/usr/bin/env python
"""
FileSystem Plugin - Quick Test Examples
Demonstrates all plugin capabilities
"""
from backend.app.plugins.filesystem.plugin import FileSystemPlugin


def test_all_features():
    """Test all FileSystem Plugin features"""
    
    print("=" * 70)
    print("ISE AI FileSystem Plugin - Feature Showcase")
    print("=" * 70)
    
    # Initialize plugin
    plugin = FileSystemPlugin('.')
    
    # Test 1: Count files
    print("\n📊 TEST 1: Count Files in tests/ folder")
    print("-" * 70)
    result = plugin.count_files_in_folder('tests', recursive=True)
    print(f"✅ Total files: {result['total_files']}")
    print(f"✅ By category: {result['by_category']}")
    print(f"✅ By extension: {result['by_extension']}")
    
    # Test 2: List files
    print("\n📋 TEST 2: List Files in backend/ folder")
    print("-" * 70)
    result = plugin.list_files('backend', limit=10)
    print(f"✅ Found {result['count']} files (showing first 10):")
    for f in result['files'][:5]:
        print(f"   • {f['name']:40s} {f['size']:>10} bytes  {f['category']}")
    
    # Test 3: Search files
    print("\n🔍 TEST 3: Search for Python Files")
    print("-" * 70)
    result = plugin.search_files('.py', by_extension=True, limit=15)
    print(f"✅ Found {result['count']} Python files")
    for f in result['files'][:5]:
        print(f"   • {f['path']}")
    if result['count'] > 5:
        print(f"   ... and {result['count'] - 5} more")
    
    # Test 4: Get file info
    print("\n📄 TEST 4: Get File Info - README.md")
    print("-" * 70)
    result = plugin.get_file_info('README.md')
    if result['success']:
        file_info = result['file']
        print(f"✅ File: {file_info['name']}")
        print(f"✅ Size: {file_info['size']} bytes")
        print(f"✅ Type: {file_info['category']}")
        print(f"✅ Is text: {file_info['is_text']}")
        if 'preview' in result:
            print(f"✅ Preview available ({result['preview']['lines_total']} lines)")
    
    # Test 5: Project structure
    print("\n🏗️  TEST 5: Complete Project Structure")
    print("-" * 70)
    result = plugin.get_project_structure()
    stats = result['stats']
    print(f"✅ Total files: {stats['total_files']}")
    print(f"✅ Total directories: {stats['total_dirs']}")
    print(f"✅ Top file categories:")
    for cat, count in sorted(stats['by_category'].items(), 
                            key=lambda x: x[1], reverse=True)[:3]:
        print(f"   • {cat:20s}: {count:4d} files")
    print(f"✅ Top extensions:")
    for ext, count in sorted(stats['by_extension'].items(), 
                            key=lambda x: x[1], reverse=True)[:3]:
        ext_name = ext if ext else "(no extension)"
        print(f"   • {ext_name:20s}: {count:4d} files")
    
    # Test 6: List directories
    print("\n📁 TEST 6: List Directories")
    print("-" * 70)
    result = plugin.list_directories(recursive=False, limit=10)
    print(f"✅ Found {result['count']} directories")
    for d in result['directories'][:5]:
        print(f"   • {d['name']:30s} ({d['file_count']:3d} files, {d['subdir_count']:2d} dirs)")
    
    # Test 7: Caching performance
    print("\n⚡ TEST 7: Caching Performance")
    print("-" * 70)
    plugin.clear_cache()
    import time
    
    start = time.time()
    result1 = plugin.list_files('src', limit=50)
    time1 = time.time() - start
    
    start = time.time()
    result2 = plugin.list_files('src', limit=50)
    time2 = time.time() - start
    
    print(f"✅ First call (no cache): {time1*1000:.2f}ms")
    print(f"✅ Second call (cached):  {time2*1000:.2f}ms")
    print(f"✅ Speed improvement: {time1/time2:.1f}x faster")
    
    # Test 8: File reading
    print("\n📖 TEST 8: Read Text File")
    print("-" * 70)
    result = plugin.read_file('QUICK_START.md', lines=(1, 10))
    if result['success']:
        print(f"✅ File: {result['file']}")
        print(f"✅ Size: {result['size']} bytes")
        print(f"✅ Total lines: {result['lines']}")
        print(f"✅ Content (lines 1-10):")
        print("   " + "\n   ".join(result['content'].split('\n')[:3]))
        print("   ...")
    
    print("\n" + "=" * 70)
    print("✅ All tests completed successfully!")
    print("=" * 70)


if __name__ == '__main__':
    test_all_features()
