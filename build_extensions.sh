#!/bin/bash

# ISE AI Extension Build and Installation Script
# Builds and installs both VS Code and JetBrains extensions

set -e

echo "🚀 ISE AI Extension Builder"
echo "=========================="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if backend is running
check_backend() {
    print_info "Checking if ISE AI backend is running..."
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        print_success "Backend is running on http://localhost:8000"
    else
        print_error "Backend is not running!"
        echo "Please start the backend first:"
        echo "  cd /home/baron/Desktop/Easv/Ai/ISE_AI"
        echo "  python main.py"
        exit 1
    fi
}

# Build VS Code Extension
build_vscode() {
    print_info "Building VS Code Extension..."
    cd "$SCRIPT_DIR/extensions/vscode"
    
    if ! command -v npm &> /dev/null; then
        print_error "npm is not installed. Please install Node.js and npm first."
        exit 1
    fi
    
    print_info "Installing dependencies..."
    npm install
    
    print_info "Compiling extension..."
    npm run compile
    
    print_info "Packaging extension..."
    if command -npx vsce &> /dev/null; then
        npx vsce package
        print_success "VS Code extension packaged successfully!"
        echo "📦 Extension file: $(ls -t *.vsix | head -1)"
        echo ""
        echo "To install in VS Code:"
        echo "  code --install-extension $(ls -t *.vsix | head -1)"
        echo ""
        echo "Or manually:"
        echo "  1. Open VS Code"
        echo "  2. Go to Extensions (Ctrl+Shift+X)"
        echo "  3. Click '...' menu"
        echo "  4. Select 'Install from VSIX...'"
        echo "  5. Choose the .vsix file"
    else
        print_info "vsce not available, extension compiled but not packaged"
        print_info "You can still test it by pressing F5 in VS Code"
    fi
    
    cd "$SCRIPT_DIR"
}

# Build JetBrains Extension
build_jetbrains() {
    print_info "Building JetBrains Extension..."
    cd "$SCRIPT_DIR/extensions/jetbrains"
    
    if ! command -v ./gradlew &> /dev/null; then
        if command -v gradle &> /dev/null; then
            print_info "Using system gradle..."
            GRADLE_CMD="gradle"
        else
            print_error "Gradle is not installed!"
            echo "Please install Gradle or download the gradle wrapper."
            exit 1
        fi
    else
        GRADLE_CMD="./gradlew"
    fi
    
    print_info "Building plugin..."
    $GRADLE_CMD clean buildPlugin
    
    print_success "JetBrains plugin built successfully!"
    
    # Find the built plugin file
    PLUGIN_FILE=$(find build/distributions -name "*.zip" | head -1)
    
    if [ -n "$PLUGIN_FILE" ]; then
        echo "📦 Plugin file: $PLUGIN_FILE"
        echo ""
        echo "To install in JetBrains IDE (PyCharm, IntelliJ, etc.):"
        echo "  1. Open your IDE"
        echo "  2. Go to Settings/Preferences"
        echo "  3. Navigate to Plugins"
        echo "  4. Click the gear icon ⚙️"
        echo "  5. Select 'Install Plugin from Disk...'"
        echo "  6. Choose the .zip file: $PLUGIN_FILE"
        echo "  7. Restart the IDE"
    else
        print_error "Plugin file not found in build/distributions/"
    fi
    
    cd "$SCRIPT_DIR"
}

# Show usage
show_usage() {
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  --all          Build both VS Code and JetBrains extensions (default)"
    echo "  --vscode       Build only VS Code extension"
    echo "  --jetbrains    Build only JetBrains extension"
    echo "  --check        Only check if backend is running"
    echo "  --help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --all"
    echo "  $0 --vscode"
    echo "  $0 --jetbrains"
}

# Main execution
main() {
    case "${1:- --all}" in
        --all)
            check_backend
            build_vscode
            echo ""
            build_jetbrains
            ;;
        --vscode)
            check_backend
            build_vscode
            ;;
        --jetbrains)
            check_backend
            build_jetbrains
            ;;
        --check)
            check_backend
            ;;
        --help)
            show_usage
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
    
    echo ""
    print_success "Build complete! 🎉"
    echo ""
    echo "📚 For more information, see:"
    echo "  - MULTI_AGENT_README.md"
    echo "  - extensions/vscode/README.md"
    echo "  - extensions/jetbrains/README.md"
}

main "$@"
