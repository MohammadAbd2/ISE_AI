import json
import tempfile
import subprocess
import sys
from pathlib import Path
from typing import Any

from app.core.config import settings

# Optional Docker-based sandbox fallback
try:
    from app.services import docker_sandbox
except Exception:
    docker_sandbox = None


def execute_module_in_sandbox(module_name: str, entrypoint: str, kwargs: dict, timeout: int = 10, use_docker: bool = False) -> dict:
    """
    Execute a module entrypoint in a subprocess sandbox. The module should be importable
    from the project root. Communicates via stdin/stdout using JSON.
    If use_docker=True and docker is available, attempt to run inside a python docker image.
    Returns a dict with status/result or error information.
    """
    project_root = Path(settings.backend_root).parent.parent

    # If docker is requested and available, delegate
    if use_docker and docker_sandbox is not None:
        try:
            return docker_sandbox.execute_in_docker(project_root, module_name, entrypoint, kwargs, timeout=timeout)
        except Exception as e:
            # Fall through to local sandbox on failure
            pass

    # Build wrapper code to run
    lines = []
    lines.append("import json,sys,traceback,importlib")
    lines.append("sys.path.insert(0, %r)" % str(project_root))
    lines.append("try:")
    lines.append("    payload = json.load(sys.stdin)")
    lines.append("    kwargs = payload.get('kwargs', {})")
    lines.append("    module = importlib.import_module(%r)" % module_name)
    lines.append("    func = getattr(module, %r)" % entrypoint)
    lines.append("    result = func(**kwargs)")
    lines.append("    print(json.dumps({'status':'success','result':result}, default=str))")
    lines.append("except Exception as e:")
    lines.append("    print(json.dumps({'status':'error','error':str(e),'trace':traceback.format_exc()}))")
    wrapper = "\n".join(lines)

    try:
        proc = subprocess.run(
            [sys.executable, "-c", wrapper],
            input=json.dumps({"kwargs": kwargs}),
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(project_root),
        )
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": f"Timed out after {timeout}s"}
    except Exception as e:
        return {"status": "error", "error": f"Failed to run sandbox: {e}"}

    stdout = proc.stdout.strip()
    stderr = proc.stderr.strip()

    if not stdout:
        return {"status": "error", "error": "No output", "stderr": stderr}

    try:
        return json.loads(stdout)
    except Exception:
        return {"status": "error", "error": "Failed to parse sandbox output", "stdout": stdout, "stderr": stderr}
