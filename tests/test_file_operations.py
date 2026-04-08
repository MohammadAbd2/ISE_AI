#!/usr/bin/env python3
"""
Test script to verify the ISE AI Agent file operation enhancements.
Run this to ensure all file operations are working correctly.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.services.tools import AgentToolbox
from app.services.chat import ChatService
from app.services.profile import ProfileService
from app.core.config import settings


async def test_file_operations():
    """Test various file operation queries."""
    
    # Initialize services
    chat_service = ChatService()
    profile_service = ProfileService()
    toolbox = AgentToolbox(chat_service=chat_service, profile_service=profile_service)
    
    print("=" * 80)
    print("TESTING ISE AI AGENT FILE OPERATIONS")
    print("=" * 80)
    
    # Test 1: Count folders
    print("\n[Test 1] Count folders in ./frontend/src")
    print("-" * 80)
    result = await toolbox.run_requested_tools("how many folders are there inside the folder ./frontend/src")
    if result:
        print(toolbox.format_direct_reply(result))
    else:
        print("❌ No result returned")
    
    # Test 2: Count files
    print("\n[Test 2] Count files in ./backend/app")
    print("-" * 80)
    result = await toolbox.run_requested_tools("how many files are in ./backend/app")
    if result:
        print(toolbox.format_direct_reply(result))
    else:
        print("❌ No result returned")
    
    # Test 3: List directories
    print("\n[Test 3] List directories in ./extensions")
    print("-" * 80)
    result = await toolbox.run_requested_tools("list folders in ./extensions")
    if result:
        print(toolbox.format_direct_reply(result))
    else:
        print("❌ No result returned")
    
    # Test 4: List files
    print("\n[Test 4] List files in ./frontend/src")
    print("-" * 80)
    result = await toolbox.run_requested_tools("list files in ./frontend/src")
    if result:
        print(toolbox.format_direct_reply(result))
    else:
        print("❌ No result returned")
    
    # Test 5: Read file content
    print("\n[Test 5] Read file content (package.json)")
    print("-" * 80)
    result = await toolbox.run_requested_tools("show me the content of package.json")
    if result:
        print(toolbox.format_direct_reply(result))
    else:
        print("❌ No result returned")
    
    print("\n" + "=" * 80)
    print("TESTS COMPLETED")
    print("=" * 80)


async def test_intent_classification():
    """Test that intents are being classified correctly."""
    from app.services.intent_classifier import get_intent_classifier
    
    print("\n" + "=" * 80)
    print("TESTING INTENT CLASSIFICATION")
    print("=" * 80)
    
    classifier = get_intent_classifier()
    
    test_queries = [
        "how many folders are there inside the folder ./frontend/src",
        "how many files are in ./backend/app",
        "display the content of main.jsx inside the folder ./frontend/src",
        "write a new file called Agent_test.txt contain 'Hi from Agent' inside the folder ./frontend/src",
        "list files in ./frontend/src",
        "show folders in ./extensions",
        "create a file called test.py in ./backend",
    ]
    
    for query in test_queries:
        intent = classifier.classify(query, "auto")
        print(f"\nQuery: {query}")
        print(f"  Intent: {intent.kind}")
        print(f"  Confidence: {intent.confidence}")
        print(f"  Use filesystem: {intent.use_filesystem}")
        print(f"  Use agent: {intent.use_agent}")


if __name__ == "__main__":
    print("Starting ISE AI Agent File Operation Tests...\n")
    
    # Run tests
    asyncio.run(test_intent_classification())
    asyncio.run(test_file_operations())
    
    print("\n✅ All tests completed!")
    print("\nNext steps:")
    print("1. Restart your backend server")
    print("2. Try these queries in the IDE plugin")
    print("3. Verify actual files are created/read/counted")
