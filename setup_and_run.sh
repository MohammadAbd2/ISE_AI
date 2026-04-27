#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
# ISE AI — One-shot setup & run script (Auto-Install Ollama Support)
# ═══════════════════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
VENV_DIR="$SCRIPT_DIR/.venv"
CERT_DIR="$SCRIPT_DIR/output/certs"
FRONTEND_CERT="$CERT_DIR/localhost-frontend.crt"
FRONTEND_KEY="$CERT_DIR/localhost-frontend.key"
ISE_AI_SCHEME="${ISE_AI_SCHEME:-auto}"  # auto | http | https

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log()   { echo -e "${GREEN}[ISE AI]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ── Ollama Installation Logic ────────────────────────────────────────────
install_ollama() {
    echo -ne "${YELLOW}[QUERY]${NC} Ollama is not installed. Would you like to install it now? (y/n): "
    read -r answer
    if [[ "$answer" =~ ^[Yy]$ ]]; then
        log "Downloading and installing Ollama..."
        # Official installation script for Linux/macOS
        curl -fsSL https://ollama.com/install.sh | sh
        
        log "Starting Ollama service in background..."
        # Start the server so models can be pulled immediately
        ollama serve > /dev/null 2>&1 &
        sleep 5 
        
        HAS_OLLAMA=true
        log "Ollama installed successfully!"
    else
        warn "Skipping Ollama installation. Local models will not be available."
        HAS_OLLAMA=false
    fi
}

# ── Check dependencies ───────────────────────────────────────────────────
check_deps() {
  log "Checking dependencies..."
  
  if ! command -v python3 &>/dev/null; then
    error "Python 3 not found. Please install Python 3.10+ first."
    exit 1
  fi

  PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
  log "Python $PYTHON_VERSION found"

  if ! command -v node &>/dev/null; then
    warn "Node.js not found — frontend will not be built. Install Node 18+."
    HAS_NODE=false
  else
    HAS_NODE=true
    log "Node $(node --version) found"
  fi

  if ! command -v ollama &>/dev/null; then
    install_ollama
  else
    HAS_OLLAMA=true
    log "Ollama found"
  fi
}

# ── Python virtual environment ───────────────────────────────────────────
setup_venv() {
  if [ ! -d "$VENV_DIR" ]; then
    log "Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
  fi
  source "$VENV_DIR/bin/activate"
  log "Virtual environment active"
}

# ── Install Python dependencies ──────────────────────────────────────────
install_python_deps() {
  log "Installing Python dependencies..."
  pip install --quiet --upgrade pip
  pip install --quiet -r "$BACKEND_DIR/requirements.txt"
  
  python3 -c "import psutil" 2>/dev/null || {
    log "Installing psutil for hardware detection..."
    pip install --quiet psutil
  }
  log "Python dependencies installed"
}

# ── Detect hardware and suggest model ────────────────────────────────────
detect_and_suggest_model() {
  log "Detecting hardware..."
  python3 << 'PYEOF'
try:
    import psutil
    mem = psutil.virtual_memory()
    total_gb = mem.total / (1024**3)
    avail_gb = mem.available / (1024**3)
    
    tier_model = {
        (0,   6):  ("qwen2.5:3b",          "tiny"),
        (6,  12):  ("qwen2.5-coder:7b",   "small"),
        (12, 22):  ("qwen2.5-coder:14b",  "medium"),
        (22, 44):  ("qwen3-30b-a3b",      "large"),
        (44, 999): ("qwen2.5:72b",        "xlarge"),
    }
    rec_model, tier = next(
        (m, t) for (lo, hi), (m, t) in tier_model.items()
        if lo <= avail_gb * 0.65 < hi
    )
    
    print(f"\n  💻 RAM: {total_gb:.1f} GB total, {avail_gb:.1f} GB available")
    print(f"  🎯 Tier: {tier}")
    print(f"  🤖 Recommended model: {rec_model}")
    print(f"  💡 Run: ollama pull {rec_model}")
except ImportError:
    print("  ⚠️  psutil not installed — install it for hardware detection")
except Exception as e:
    print(f"  ⚠️  Hardware detection failed: {e}")
PYEOF
}

# ── .env setup ───────────────────────────────────────────────────────────
setup_env() {
  if [ ! -f "$BACKEND_DIR/.env" ]; then
    log "Creating .env from template..."
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
    warn "Review and update $BACKEND_DIR/.env before running in production."
  else
    log ".env already exists, skipping"
  fi
}

# ── Pull Ollama model ─────────────────────────────────────────────────────
pull_model() {
  if [ "${HAS_OLLAMA:-false}" = "true" ]; then
    DEFAULT_MODEL=$(grep -E "^DEFAULT_MODEL=" "$BACKEND_DIR/.env" 2>/dev/null | cut -d= -f2 | tr -d '"' | tr -d "'") || true
    
    if [ "$DEFAULT_MODEL" = "auto" ] || [ -z "$DEFAULT_MODEL" ]; then
      log "Model set to 'auto' — will be selected at runtime based on hardware"
    else
      log "Pulling Ollama model: $DEFAULT_MODEL"
      ollama pull "$DEFAULT_MODEL" || warn "Could not pull $DEFAULT_MODEL — check if Ollama is running"
    fi
  fi
}


ensure_local_https_certs() {
  mkdir -p "$CERT_DIR"

  if [ "$ISE_AI_SCHEME" = "http" ]; then
    USE_HTTPS=false
    log "Frontend scheme forced to HTTP by ISE_AI_SCHEME=http"
    return
  fi

  if [ "$ISE_AI_SCHEME" = "auto" ] && ! command -v mkcert &>/dev/null; then
    USE_HTTPS=false
    warn "mkcert is not installed, so the frontend will use HTTP to avoid browser certificate/download errors."
    warn "Install mkcert for trusted HTTPS, or force self-signed HTTPS with ISE_AI_SCHEME=https."
    return
  fi

  if command -v mkcert &>/dev/null; then
    if [ ! -f "$FRONTEND_CERT" ] || [ ! -f "$FRONTEND_KEY" ]; then
      log "Generating trusted local HTTPS certificate with mkcert..."
      mkcert -install >/dev/null 2>&1 || true
      mkcert -cert-file "$FRONTEND_CERT" -key-file "$FRONTEND_KEY" localhost 127.0.0.1 ::1 >/dev/null 2>&1 || {
        warn "mkcert failed — falling back to self-signed OpenSSL certificate."
      }
    fi
  fi

  if [ ! -f "$FRONTEND_CERT" ] || [ ! -f "$FRONTEND_KEY" ]; then
    if ! command -v openssl &>/dev/null; then
      warn "OpenSSL not found — HTTPS certificates cannot be generated. Falling back to HTTP."
      USE_HTTPS=false
      return
    fi
    log "Generating local HTTPS certificate for frontend..."
    openssl req -x509 -nodes -newkey rsa:2048 -sha256 -days 365       -keyout "$FRONTEND_KEY" -out "$FRONTEND_CERT"       -subj "/CN=localhost"       -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" >/dev/null 2>&1
    warn "The generated certificate is self-signed. Install mkcert for a browser-trusted local certificate."
  fi
  USE_HTTPS=true
}

# ── Frontend ──────────────────────────────────────────────────────────────
setup_frontend() {
  if [ "$HAS_NODE" = "true" ]; then
    log "Installing frontend dependencies..."
    cd "$FRONTEND_DIR"
    # Clean up potentially broken node_modules from packaging
    if [ -d "node_modules" ]; then
        warn "Cleaning up existing node_modules to prevent module resolution errors..."
        rm -rf node_modules
    fi
    npm install --silent
    log "Frontend dependencies installed"
    cd "$SCRIPT_DIR"
  fi
}

# ── Start services ────────────────────────────────────────────────────────
start_services() {
  log "Starting ISE AI..."
  echo ""
  echo -e "${BLUE}  ╔══════════════════════════════════════╗"
  echo    "  ║         ISE AI v2.0.0                ║"
  echo    "  ║  Self-improving coding assistant     ║"
  echo -e "  ╚══════════════════════════════════════╝${NC}"
  echo ""
  log "Backend  → http://localhost:8000"
  if [ "${USE_HTTPS:-false}" = "true" ]; then
    [ "$HAS_NODE" = "true" ] && log "Frontend → https://localhost:5173"
    if command -v mkcert &>/dev/null; then
      log "Local HTTPS uses a mkcert-issued certificate when available."
    else
      warn "Frontend HTTPS is self-signed. Downloads and microphone access may be blocked unless you trust the cert. Use ISE_AI_SCHEME=http or install mkcert."
    fi
  else
    [ "$HAS_NODE" = "true" ] && log "Frontend → http://localhost:5173"
  fi
  echo ""

  source "$VENV_DIR/bin/activate"
  cd "$BACKEND_DIR"
  python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
  BACKEND_PID=$!

  if [ "$HAS_NODE" = "true" ]; then
    cd "$FRONTEND_DIR"
    if [ "${USE_HTTPS:-false}" = "true" ]; then
      HTTPS_CERT_FILE="$FRONTEND_CERT" HTTPS_KEY_FILE="$FRONTEND_KEY" VITE_BACKEND_TARGET="http://localhost:8000" npm run dev &
    else
      VITE_BACKEND_TARGET="http://localhost:8000" npm run dev &
    fi
    FRONTEND_PID=$!
  fi

  # Clean up processes on exit
  trap "kill $BACKEND_PID ${FRONTEND_PID:-} 2>/dev/null; log 'Stopped'; exit 0" SIGINT SIGTERM

  log "Running. Press Ctrl+C to stop."
  wait
}

# ── Main ──────────────────────────────────────────────────────────────────
main() {
  echo ""
  log "ISE AI Setup & Run"
  
  check_deps
  setup_venv
  install_python_deps
  detect_and_suggest_model
  setup_env
  ensure_local_https_certs
  pull_model
  setup_frontend
  start_services
}

main "$@"
