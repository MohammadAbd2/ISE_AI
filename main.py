"""Convenience entrypoint for local backend development."""

import sys
from pathlib import Path
import uvicorn

if __name__ == "__main__":
    # Add backend directory to Python path so 'app' imports work
    backend_dir = Path(__file__).parent / "backend"
    sys.path.insert(0, str(backend_dir))
    
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
