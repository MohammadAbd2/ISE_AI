#!/bin/bash

# ISE AI Multi-Agent Quick Start Script
# This script helps you set up and test the enhanced multi-agent system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         ISE AI Multi-Agent Setup Script               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to print colored messages
print_message() {
    echo -e "${GREEN}[ISE AI]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    print_error "Please run this script from the ISE_AI root directory"
    exit 1
fi

print_message "Starting ISE AI Multi-Agent System Setup..."
echo ""

# Step 1: Check Python environment
print_message "Step 1: Checking Python environment..."
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    print_error "Python not found. Please install Python 3.8+"
    exit 1
fi

print_message "Using Python: $($PYTHON --version)"
echo ""

# Step 2: Install backend dependencies
print_message "Step 2: Installing backend dependencies..."
cd backend
if [ ! -d ".venv" ]; then
    print_message "Creating virtual environment..."
    $PYTHON -m venv .venv
fi

source .venv/bin/activate
pip install -q -r requirements.txt
cd ..
print_message "Backend dependencies installed ✓"
echo ""

# Step 3: Setup VS Code Extension
print_message "Step 3: Setting up VS Code Extension..."
if command -v node &> /dev/null; then
    cd extensions/vscode
    if [ ! -d "node_modules" ]; then
        npm install
    fi
    npm run compile
    cd ../..
    print_message "VS Code Extension compiled ✓"
else
    print_warning "Node.js not found. Skipping VS Code Extension setup."
    print_warning "To setup later, run: cd extensions/vscode && npm install && npm run compile"
fi
echo ""

# Step 4: Setup JetBrains Plugin
print_message "Step 4: Setting up JetBrains Plugin..."
if command -v ./gradlew &> /dev/null || command -v gradle &> /dev/null; then
    cd extensions/jetbrains
    if [ ! -f "gradlew" ]; then
        print_warning "Gradle wrapper not found. You'll need to build manually."
    else
        chmod +x gradlew
        ./gradlew buildPlugin
        print_message "JetBrains Plugin built ✓"
    fi
    cd ../..
else
    print_warning "Gradle not found. Skipping JetBrains Plugin setup."
    print_warning "To setup later, run: cd extensions/jetbrains && ./gradlew buildPlugin"
fi
echo ""

# Step 5: Create configuration
print_message "Step 5: Creating default configuration..."
CONFIG_DIR="$HOME/.ise_ai"
mkdir -p "$CONFIG_DIR"

if [ ! -f "$CONFIG_DIR/config.json" ]; then
    cat > "$CONFIG_DIR/config.json" << 'EOF'
{
  "version": "1.0.0",
  "enable_multi_agent": true,
  "default_agent": "coding-agent",
  "max_concurrent_tasks": 5,
  "task_timeout_seconds": 300,
  "enable_agent_communication": true,
  "enable_task_delegation": true,
  "enable_context_sharing": true,
  "agents": {
    "planning-agent": {
      "name": "planning-agent",
      "enabled": true,
      "max_retries": 3,
      "timeout_seconds": 120
    },
    "coding-agent": {
      "name": "coding-agent",
      "enabled": true,
      "max_retries": 3,
      "timeout_seconds": 120
    },
    "research-agent": {
      "name": "research-agent",
      "enabled": true,
      "max_retries": 3,
      "timeout_seconds": 120
    },
    "review-agent": {
      "name": "review-agent",
      "enabled": true,
      "max_retries": 3,
      "timeout_seconds": 120
    },
    "testing-agent": {
      "name": "testing-agent",
      "enabled": true,
      "max_retries": 3,
      "timeout_seconds": 120
    },
    "documentation-agent": {
      "name": "documentation-agent",
      "enabled": true,
      "max_retries": 3,
      "timeout_seconds": 120
    }
  }
}
EOF
    print_message "Configuration created at $CONFIG_DIR/config.json ✓"
else
    print_message "Configuration already exists ✓"
fi
echo ""

# Step 6: Start backend
print_message "Step 6: Starting ISE AI Backend..."
print_message "The backend will start on http://localhost:8000"
print_message "Press Ctrl+C to stop the server"
echo ""
print_warning "Starting backend in background..."

# Start backend in background
$PYTHON main.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Check if backend is running
if kill -0 $BACKEND_PID 2>/dev/null; then
    print_message "Backend started successfully (PID: $BACKEND_PID) ✓"
else
    print_error "Failed to start backend"
    exit 1
fi
echo ""

# Step 7: Test the system
print_message "Step 7: Testing multi-agent system..."
sleep 2

# Test health endpoint
if curl -s http://localhost:8000/health | grep -q "ok"; then
    print_message "Health check passed ✓"
else
    print_warning "Health check failed - backend may still be starting"
fi

# Test agent status
if curl -s http://localhost:8000/api/agents/status | grep -q "planning-agent"; then
    print_message "Multi-agent system is operational ✓"
else
    print_warning "Agent status check failed - may need to wait longer"
fi
echo ""

# Print summary
echo ""
print_message "╔════════════════════════════════════════════════════════╗"
print_message "║          Setup Complete! 🎉                            ║"
print_message "╚════════════════════════════════════════════════════════╝"
echo ""
print_message "Your ISE AI Multi-Agent System is ready!"
echo ""
print_message "Backend: http://localhost:8000"
print_message "Backend PID: $BACKEND_PID"
echo ""
print_message "Next Steps:"
echo ""
print_message "1. Install VS Code Extension:"
print_message "   cd extensions/vscode"
print_message "   code --install-extension ise-ai-copilot-1.0.0.vsix"
echo ""
print_message "2. Install JetBrains Plugin:"
print_message "   cd extensions/jetbrains"
print_message "   # Install from build/distributions/ in your IDE"
echo ""
print_message "3. Test the system:"
print_message "   - Open VS Code or JetBrains IDE"
print_message "   - Press Ctrl+Shift+I to open chat"
print_message "   - Try: 'Create a FastAPI endpoint for user authentication'"
echo ""
print_message "4. Read the full documentation:"
print_message "   cat MULTI_AGENT_README.md"
echo ""
print_warning "To stop the backend: kill $BACKEND_PID"
echo ""
print_message "Happy coding with your AI Copilot! 🚀"
echo ""

# Keep script running to show logs
print_message "Backend is running. Press Ctrl+C to stop."
wait $BACKEND_PID
