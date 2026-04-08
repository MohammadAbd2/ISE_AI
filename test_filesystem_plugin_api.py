#!/usr/bin/env python
"""
FileSystem Plugin API Test Suite
Test all REST API endpoints
"""
import httpx
import asyncio
import json
from pathlib import Path


BASE_URL = "http://localhost:8000/api/filesystem"


async def test_api():
    """Test all FileSystem Plugin API endpoints"""
    
    async with httpx.AsyncClient(timeout=30) as client:
        print("=" * 70)
        print("ISE AI FileSystem Plugin - API Test Suite")
        print("=" * 70)
        print(f"Base URL: {BASE_URL}")
        print()
        
        # Test 1: Health check
        print("📍 TEST 1: Health Check")
        print("-" * 70)
        try:
            response = await client.get(f"{BASE_URL}/health")
            print(f"✅ Status: {response.status_code}")
            data = response.json()
            print(f"✅ Response: {json.dumps(data, indent=2)}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Test 2: Count files
        print("\n📊 TEST 2: Count Files in tests/")
        print("-" * 70)
        try:
            response = await client.get(f"{BASE_URL}/count", params={
                "folder": "tests",
                "recursive": False
            })
            print(f"✅ Status: {response.status_code}")
            data = response.json()
            if data.get('success'):
                print(f"✅ Total files: {data['total_files']}")
                print(f"✅ By category: {data['by_category']}")
            else:
                print(f"❌ Error: {data.get('error')}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Test 3: List files
        print("\n📋 TEST 3: List Files in backend/")
        print("-" * 70)
        try:
            response = await client.get(f"{BASE_URL}/list", params={
                "folder": "backend",
                "limit": 5
            })
            print(f"✅ Status: {response.status_code}")
            data = response.json()
            if data.get('success'):
                print(f"✅ Found {data['count']} files:")
                for f in data['files'][:3]:
                    print(f"   • {f['name']:30s} ({f['size']:>8d} bytes)")
            else:
                print(f"❌ Error: {data.get('error')}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Test 4: List directories
        print("\n📁 TEST 4: List Directories")
        print("-" * 70)
        try:
            response = await client.get(f"{BASE_URL}/directories", params={
                "limit": 5
            })
            print(f"✅ Status: {response.status_code}")
            data = response.json()
            if data.get('success'):
                print(f"✅ Found {data['count']} directories:")
                for d in data['directories'][:3]:
                    print(f"   • {d['name']:30s} ({d['file_count']:2d} files)")
            else:
                print(f"❌ Error: {data.get('error')}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Test 5: Search files
        print("\n🔍 TEST 5: Search for .py Files")
        print("-" * 70)
        try:
            response = await client.get(f"{BASE_URL}/search", params={
                "pattern": ".py",
                "by_extension": True,
                "limit": 5
            })
            print(f"✅ Status: {response.status_code}")
            data = response.json()
            if data.get('success'):
                print(f"✅ Found {data['count']} Python files")
                for f in data['files'][:3]:
                    print(f"   • {f['path']}")
            else:
                print(f"❌ Error: {data.get('error')}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Test 6: Get file info
        print("\n📄 TEST 6: Get File Info - README.md")
        print("-" * 70)
        try:
            response = await client.get(f"{BASE_URL}/info/README.md")
            print(f"✅ Status: {response.status_code}")
            data = response.json()
            if data.get('success'):
                f = data['file']
                print(f"✅ File: {f['name']}")
                print(f"✅ Size: {f['size']} bytes")
                print(f"✅ Category: {f['category']}")
                print(f"✅ Is text: {f['is_text']}")
            else:
                print(f"❌ Error: {data.get('error')}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Test 7: Read file
        print("\n📖 TEST 7: Read File - QUICK_START.md (lines 1-5)")
        print("-" * 70)
        try:
            response = await client.get(f"{BASE_URL}/read/QUICK_START.md", params={
                "start_line": 1,
                "end_line": 5
            })
            print(f"✅ Status: {response.status_code}")
            data = response.json()
            if data.get('success'):
                print(f"✅ File: {data['file']}")
                print(f"✅ Lines: {data['lines']}")
                content_preview = data['content'][:200]
                print(f"✅ Content preview:\n{content_preview}...")
            else:
                print(f"❌ Error: {data.get('error')}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Test 8: Project structure
        print("\n🏗️  TEST 8: Project Structure")
        print("-" * 70)
        try:
            response = await client.get(f"{BASE_URL}/structure")
            print(f"✅ Status: {response.status_code}")
            data = response.json()
            if data.get('success'):
                stats = data['stats']
                print(f"✅ Total files: {stats['total_files']}")
                print(f"✅ Total directories: {stats['total_dirs']}")
                print(f"✅ Top categories:")
                for cat, count in sorted(stats['by_category'].items(),
                                       key=lambda x: x[1], reverse=True)[:3]:
                    print(f"   • {cat:20s}: {count:4d} files")
            else:
                print(f"❌ Error: {data.get('error')}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Test 9: Stats
        print("\n📈 TEST 9: Statistics for /tests")
        print("-" * 70)
        try:
            response = await client.get(f"{BASE_URL}/stats", params={
                "folder": "tests"
            })
            print(f"✅ Status: {response.status_code}")
            data = response.json()
            if data.get('success'):
                print(f"✅ Total files: {data.get('total_files')}")
                print(f"✅ Response keys: {list(data.keys())}")
            else:
                print(f"❌ Error: {data.get('error')}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Test 10: Clear cache
        print("\n🔄 TEST 10: Clear Cache")
        print("-" * 70)
        try:
            response = await client.post(f"{BASE_URL}/cache/clear")
            print(f"✅ Status: {response.status_code}")
            data = response.json()
            print(f"✅ Response: {data}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("\n" + "=" * 70)
        print("✅ API Tests Completed!")
        print("=" * 70)
        print("\nNote: Make sure the ISE AI backend is running on http://localhost:8000")
        print("Start with: python main.py or uvicorn app.main:app --reload")


if __name__ == '__main__':
    print("\n⚠️  Make sure ISE AI backend is running on http://localhost:8000")
    print("To start: cd backend && python main.py\n")
    
    try:
        asyncio.run(test_api())
    except Exception as e:
        print(f"❌ Failed to run tests: {e}")
        print("\nMake sure the backend is running at http://localhost:8000")
