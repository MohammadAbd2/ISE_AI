import subprocess
import json
import sys
from pathlib import Path
from typing import Dict


def docker_available() -> bool:
    try:
        subprocess.run(["docker", "--version"], capture_output=True, check=True)
        return True
    except Exception:
        return False


def execute_in_docker(project_root: Path, module_name: str, entrypoint: str, kwargs: Dict, timeout: int = 20) -> Dict:
    """
    Attempt to run the module inside a lightweight python docker image.
    Falls back to returning an error if docker isn't available.
    """
    if not docker_available():
        return {"status": "error", "error": "Docker not available on host"}

    wrapper = (
        "import json,sys,traceback,importlib\n"
        "payload = json.load(sys.stdin)\n"
        "kwargs = payload.get('kwargs', {})\n"
        "try:\n"
        f"    module = importlib.import_module({repr(module_name)})\n"
        f"    func = getattr(module, {repr(entrypoint)})\n"
        "    result = func(**kwargs)\n"
        "    print(json.dumps({'status': 'success', 'result': result}, default=str))\n"
        "except Exception as e:\n"
        "    print(json.dumps({'status': 'error', 'error': str(e), 'trace': traceback.format_exc()}))\n"
    )

    # Build docker command
    cmd = [
        "docker",
        "run",
        "--rm",
        "-i",
        "-v",
        f"{str(project_root)}:/workspace",
        "-w",
        "/workspace",
        "python:3.11-slim",
        "python",
        "-c",
        wrapper,
    ]

    try:
        proc = subprocess.run(
            cmd,
            input=json.dumps({"kwargs": kwargs}),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": f"Docker execution timed out after {timeout}s"}
    except Exception as e:
        return {"status": "error", "error": f"Failed to run docker: {e}"}

    stdout = proc.stdout.strip()
    stderr = proc.stderr.strip()

    if not stdout:
        return {"status": "error", "error": "No output from docker", "stderr": stderr}

    try:
        return json.loads(stdout)
    except Exception:
        return {"status": "error", "error": "Failed to parse docker output", "stdout": stdout, "stderr": stderr}
