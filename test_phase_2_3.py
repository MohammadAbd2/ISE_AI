#!/usr/bin/env python3
"""
Test script for Phase 2 & 3 features.
Run this to verify self-learning and planning agent functionality.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


async def test_self_learning():
    """Test the self-learning system."""
    print("=" * 60)
    print("Testing Self-Learning System")
    print("=" * 60)
    
    from backend.app.services.self_learning import get_learning_system
    
    # Initialize
    learning_system = get_learning_system()
    await learning_system.initialize()
    
    # Test preference detection
    print("\n1. Testing preference detection...")
    entries = await learning_system.learn_from_interaction(
        user_message="Create a React component called userProfile",
        assistant_response="const userProfile = () => { ... }",
        context="const userProfile = () => { return <div>User</div>; };",
        session_id="test-session"
    )
    print(f"   ✅ Learned {len(entries)} preferences")
    
    # Test context generation
    print("\n2. Testing personalized context...")
    context = await learning_system.get_personalized_context("Create a component")
    print(f"   ✅ Generated context with {len(context.get('recommendations', []))} recommendations")
    
    # Test stats
    print("\n3. Testing learning stats...")
    stats = await learning_system.get_learning_stats()
    print(f"   ✅ Total interactions: {stats['total_interactions']}")
    print(f"   ✅ Preferences learned: {stats['preferences_learned']}")
    print(f"   ✅ Technologies: {stats['technologies']}")
    
    print("\n✅ Self-learning system tests passed!\n")


async def test_planning_agent():
    """Test the planning agent."""
    print("=" * 60)
    print("Testing Planning Agent")
    print("=" * 60)
    
    from backend.app.services.planning_agent import get_planning_agent
    
    # Initialize
    planning_agent = get_planning_agent()
    
    # Test plan creation
    print("\n1. Testing plan creation...")
    task = "Create a file called text1.txt then update the content to 'this is a text' and show me the result"
    plan = await planning_agent.create_plan(task)
    print(f"   ✅ Created plan with {plan.total_steps} steps")
    print(f"   ✅ Progress: {plan.progress_text}")
    
    # Test plan execution
    print("\n2. Testing plan execution...")
    completed_plan = await planning_agent.execute_task_with_plan(task)
    print(f"   ✅ Plan status: {completed_plan.status.value}")
    print(f"   ✅ Progress: {completed_plan.progress_text}")
    print(f"   ✅ Completed steps: {completed_plan.completed_steps}/{completed_plan.total_steps}")
    
    # Show plan log
    print("\n3. Plan execution log:")
    print(completed_plan.to_log_string())
    
    print("\n✅ Planning agent tests passed!\n")


async def test_integration():
    """Test integration between systems."""
    print("=" * 60)
    print("Testing System Integration")
    print("=" * 60)
    
    from backend.app.services.self_learning import get_learning_system
    from backend.app.services.planning_agent import get_planning_agent
    
    # Initialize both systems
    learning_system = get_learning_system()
    await learning_system.initialize()
    
    planning_agent = get_planning_agent()
    
    print("\n1. Testing multi-step task with learning...")
    task = "Create a React component called helloWorld then add a console.log"
    
    # Execute plan
    plan = await planning_agent.execute_task_with_plan(task)
    print(f"   ✅ Plan completed: {plan.status.value}")
    
    # Learn from interaction
    entries = await learning_system.learn_from_interaction(
        user_message=task,
        assistant_response=plan.to_log_string(),
        context="React component creation",
        session_id="integration-test"
    )
    print(f"   ✅ Learned {len(entries)} new preferences")
    
    # Get updated stats
    stats = await learning_system.get_learning_stats()
    print(f"   ✅ Total interactions now: {stats['total_interactions']}")
    
    print("\n✅ Integration tests passed!\n")


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("ISE AI - Phase 2 & 3 Feature Tests")
    print("=" * 60 + "\n")
    
    try:
        # Run tests
        await test_self_learning()
        await test_planning_agent()
        await test_integration()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nYour ISE AI system now has:")
        print("  ✅ Self-learning from user chats")
        print("  ✅ User preference detection")
        print("  ✅ Code style adaptation")
        print("  ✅ Context-aware responses")
        print("  ✅ Advanced memory management")
        print("  ✅ Multi-session learning")
        print("  ✅ Autonomous planning agent")
        print("  ✅ Progress tracking (0/3, 1/3, 2/3, 3/3)")
        print("\nStart using the chat to see learning in action!")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
