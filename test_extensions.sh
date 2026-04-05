#!/bin/bash

# ISE AI Extension Test Script
# Tests the multi-agent system and IDE extensions

set -e

echo "🧪 ISE AI Extension Test Suite"
echo "==============================="

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0

# Test counter
test_number=0

# Function to run a test
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_output="$3"
    
    test_number=$((test_number + 1))
    echo ""
    echo -e "${BLUE}Test $test_number: $test_name${NC}"
    
    if eval "$test_command" 2>&1 | grep -q "$expected_output"; then
        echo -e "${GREEN}  ✅ PASS${NC}"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}  ❌ FAIL${NC}"
        FAIL=$((FAIL + 1))
    fi
}

# Function to run a test with warning
run_test_warn() {
    local test_name="$1"
    local test_command="$2"
    local expected_output="$3"
    
    test_number=$((test_number + 1))
    echo ""
    echo -e "${BLUE}Test $test_name${NC}"
    
    if eval "$test_command" 2>&1 | grep -q "$expected_output"; then
        echo -e "${GREEN}  ✅ PASS${NC}"
        PASS=$((PASS + 1))
    else
        echo -e "${YELLOW}  ⚠️  WARN${NC}"
        WARN=$((WARN + 1))
    fi
}

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Phase 1: Backend Tests${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Test 1: Backend Health Check
run_test "Backend Health Check" \
    "curl -s http://localhost:8000/health" \
    '"status": "ok"'

# Test 2: Multi-Agent Status
run_test "Multi-Agent System Status" \
    "curl -s http://localhost:8000/api/agents/status" \
    'agent_name'

# Test 3: Agent Roles
run_test "Agent Roles Available" \
    "curl -s http://localhost:8000/api/agents/roles" \
    'planner'

# Test 4: Simple Chat Request
run_test "Simple Chat Request" \
    "curl -s -X POST http://localhost:8000/api/chat -H 'Content-Type: application/json' -d '{\"message\": \"Hello\"}'" \
    'message'

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Phase 2: Multi-Agent Tests${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Test 5: Single Agent Execution
run_test "Single Agent Execution" \
    "curl -s -X POST http://localhost:8000/api/agents/execute -H 'Content-Type: application/json' -d '{\"description\": \"Create a simple Python function\", \"multi_agent\": false}'" \
    'result'

# Test 6: Multi-Agent Execution
run_test "Multi-Agent Execution" \
    "curl -s -X POST http://localhost:8000/api/agents/execute -H 'Content-Type: application/json' -d '{\"description\": \"Create a FastAPI endpoint\", \"multi_agent\": true}'" \
    'result'

# Test 7: Task Status
run_test_warn "Task Status Check" \
    "curl -s http://localhost:8000/api/agents/tasks/test-task" \
    'task_id\|not found'

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Phase 3: Extension Build Tests${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Test 8: VS Code Extension Files
run_test "VS Code Extension Files Exist" \
    "test -f extensions/vscode/package.json && test -f extensions/vscode/src/extension.ts" \
    ''

# Test 9: JetBrains Extension Files
run_test "JetBrains Extension Files Exist" \
    "test -f extensions/jetbrains/build.gradle.kts && test -f extensions/jetbrains/src/main/kotlin/com/ise/ai/copilot/service/ISEAIService.kt" \
    ''

# Test 10: VS Code Dependencies
run_test_warn "VS Code Dependencies (npm)" \
    "cd extensions/vscode && npm list --depth=0 2>&1 | head -1" \
    'ise-ai-copilot'

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Phase 4: Python Backend Tests${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Test 11: Python Imports
run_test "Python Multi-Agent Import" \
    "cd /home/baron/Desktop/Easv/Ai/ISE_AI && python -c 'from backend.app.services.multi_agent_orchestrator import MultiAgentOrchestrator; print(\"Import successful\")'" \
    'Import successful'

# Test 12: Orchestrator Initialization
run_test "Orchestrator Initialization" \
    "cd /home/baron/Desktop/Easv/Ai/ISE_AI && python -c 'from backend.app.services.multi_agent_orchestrator import get_multi_agent_orchestrator; orchestrator = get_multi_agent_orchestrator(); print(\"Orchestrator ready\")'" \
    'ready'

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Phase 5: Integration Tests${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Test 13: Complex Multi-Agent Task
run_test "Complex Multi-Agent Task" \
    "curl -s -X POST http://localhost:8000/api/agents/execute -H 'Content-Type: application/json' -d '{\"description\": \"Create a Python function to calculate factorial with tests\", \"multi_agent\": true}'" \
    'result\|used_agents'

# Test 14: Streaming Endpoint
run_test_warn "Streaming Endpoint Available" \
    "curl -s -X POST http://localhost:8000/api/chat/stream -H 'Content-Type: application/json' -d '{\"message\": \"Hello\"}' | head -1" \
    'type'

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo ""
echo -e "Total Tests: $test_number"
echo -e "${GREEN}Passed: $PASS${NC}"
echo -e "${RED}Failed: $FAIL${NC}"
echo -e "${YELLOW}Warnings: $WARN${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✅ All critical tests passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Build extensions: ./build_extensions.sh"
    echo "  2. Install in your IDE"
    echo "  3. Start coding with AI assistance!"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Please check the errors above.${NC}"
    echo ""
    echo "Common issues:"
    echo "  - Backend not running (start with: python main.py)"
    echo "  - Missing dependencies (run: pip install -r requirements.txt)"
    echo "  - Port conflicts (check if port 8000 is in use)"
    exit 1
fi
